#!/usr/bin/env python3
"""Deterministic lifecycle controller for self-authored Codex plugins."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile
from datetime import datetime, timezone
from pathlib import Path


FINAL_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache"}
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


class LifecycleError(RuntimeError):
    """A stable, user-actionable lifecycle failure."""


def fail(code: str, message: str):
    raise LifecycleError(f"{code}: {redact(message)}")


def redact(value: str) -> str:
    def replace(match):
        parsed = urllib.parse.urlsplit(match.group(0))
        host = parsed.hostname or ""
        if parsed.port:
            host += f":{parsed.port}"
        return urllib.parse.urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))

    return re.sub(r"https?://[^\s/]+@[^\s]+", replace, value)


def require_final_semver(value: str) -> tuple[int, int, int]:
    match = FINAL_SEMVER.fullmatch(value)
    if not match:
        fail("E_VERSION", f"formal version must be final strict SemVer, got {value!r}")
    return tuple(int(part) for part in match.groups())


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail("E_JSON", f"cannot read {path}: {exc}")


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(raw_temp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _walk(root: Path):
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in sorted(directories + files):
            path = current_path / name
            if path.is_symlink():
                yield path
        directories[:] = sorted(
            name
            for name in directories
            if name not in SKIP_PARTS and not (current_path / name).is_symlink()
        )
        for name in sorted(files):
            path = current_path / name
            if not path.is_symlink() and not any(part in SKIP_PARTS for part in path.parts):
                yield path


def hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in _walk(root):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix().encode()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(path.read_bytes())
    return digest.hexdigest()


def same_tree(left: Path, right: Path) -> bool:
    return left.is_dir() and right.is_dir() and hash_tree(left) == hash_tree(right)


def frontmatter_name(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        fail("E_SKILL_FRONTMATTER", f"missing YAML frontmatter in {path}")
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip("'\"")
            if name:
                return name
    fail("E_SKILL_NAME", f"missing Skill name in {path}")


def inspect_roots(roots: list[Path]) -> dict:
    skills = []
    symlinks = []
    by_name: dict[str, list[str]] = {}
    for raw_root in roots:
        root = Path(raw_root).resolve()
        if not root.exists():
            continue
        for path in _walk(root):
            if path.is_symlink():
                symlinks.append(str(path))
            elif path.name == "SKILL.md":
                name = frontmatter_name(path)
                record = {
                    "name": name,
                    "path": str(path),
                    "sha256": hash_tree(path.parent),
                }
                skills.append(record)
                by_name.setdefault(name, []).append(str(path))
    duplicates = {name: paths for name, paths in by_name.items() if len(paths) > 1}
    return {
        "roots": [str(Path(root)) for root in roots],
        "skills": sorted(skills, key=lambda item: (item["name"], item["path"])),
        "duplicates": duplicates,
        "symlinks": sorted(set(symlinks)),
        "formal_ready": not duplicates and not symlinks,
    }


def git_run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=False
    )
    if check and result.returncode:
        fail("E_GIT", result.stderr.strip() or result.stdout.strip() or "git command failed")
    return result


def git_output(repo: Path, *args: str) -> str:
    return git_run(repo, *args).stdout.strip()


def load_repo(repo: Path) -> tuple[dict, Path, dict]:
    repo = repo.resolve()
    config = read_json(repo / "lifecycle.json")
    plugin_relative = Path(config.get("plugin_path", "."))
    if plugin_relative.is_absolute() or ".." in plugin_relative.parts:
        fail("E_PLUGIN_PATH", f"plugin_path escapes repository: {plugin_relative}")
    plugin = (repo / plugin_relative).resolve()
    try:
        plugin.relative_to(repo)
    except ValueError:
        fail("E_PLUGIN_PATH", f"plugin_path escapes repository: {plugin}")
    manifest = read_json(plugin / ".codex-plugin" / "plugin.json")
    if not isinstance(manifest.get("name"), str) or not manifest["name"]:
        fail("E_MANIFEST", "plugin manifest requires a non-empty name")
    return config, plugin, manifest


def set_manifest_version(repo: Path, version: str) -> None:
    require_final_semver(version)
    _, plugin, manifest = load_repo(repo)
    manifest["version"] = version
    atomic_json(plugin / ".codex-plugin" / "plugin.json", manifest)


def _payload_paths(plugin: Path):
    for path in _walk(plugin):
        if path.is_symlink():
            fail("E_SYMLINK", f"Plugin payload contains symlink: {path}")
        if path.is_file():
            yield path


def build_artifact(repo: Path, output: Path) -> dict:
    repo = Path(repo).resolve()
    output = Path(output).resolve()
    _, plugin, manifest = load_repo(repo)
    require_final_semver(manifest.get("version", ""))
    paths = sorted(_payload_paths(plugin), key=lambda path: path.relative_to(plugin).as_posix())
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    os.close(fd)
    temp = Path(raw_temp)
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in paths:
                if path == output or path == temp:
                    continue
                name = path.relative_to(plugin).as_posix()
                info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                # The formal artifact is data consumed by Codex; normalize modes so
                # the same commit hashes identically on native Linux and DrvFs.
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes(), compresslevel=9)
        os.replace(temp, output)
    finally:
        temp.unlink(missing_ok=True)
    return {
        "plugin": manifest["name"],
        "version": manifest["version"],
        "artifact": str(output),
        "sha256": sha256_file(output),
    }


def _run_checks(repo: Path, config: dict) -> None:
    checks = config.get("checks", [])
    if not isinstance(checks, list):
        fail("E_CHECK_CONFIG", "checks must be a list of argument arrays")
    for command in checks:
        if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
            fail("E_CHECK_CONFIG", f"invalid check command: {command!r}")
        result = subprocess.run(command, cwd=repo, text=True, capture_output=True, check=False)
        if result.returncode:
            fail("E_CHECK_FAILED", result.stderr.strip() or result.stdout.strip() or repr(command))


def promotion_preflight(repo: Path, version: str) -> dict:
    repo = Path(repo).resolve()
    require_final_semver(version)
    config, plugin, manifest = load_repo(repo)
    if manifest.get("version") != version:
        fail("E_VERSION_MISMATCH", f"manifest {manifest.get('version')!r} != requested {version!r}")
    if git_output(repo, "status", "--porcelain"):
        fail("E_GIT_DIRTY", f"repository is not clean: {repo}")
    branch = git_output(repo, "branch", "--show-current")
    if branch != "develop":
        fail("E_GIT_BRANCH", f"promotion must start on develop, got {branch!r}")
    branches = {
        line.strip()
        for line in git_output(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()
        if line.strip()
    }
    if branches != {"main", "develop"}:
        fail("E_GIT_BRANCH_SET", f"local permanent branches must be main/develop, got {sorted(branches)}")
    ancestor = git_run(repo, "merge-base", "--is-ancestor", "main", "develop", check=False)
    if ancestor.returncode:
        fail("E_GIT_DIVERGED", "main is not an ancestor of develop")
    audit_roots = [plugin]
    for raw in config.get("discovery_roots", []):
        candidate = Path(raw).expanduser()
        audit_roots.append(candidate.resolve() if candidate.is_absolute() else (repo / candidate).resolve())
    report = inspect_roots(audit_roots)
    if not report["formal_ready"]:
        fail("E_DISCOVERY", json.dumps({"duplicates": report["duplicates"], "symlinks": report["symlinks"]}))
    _run_checks(repo, config)
    return {
        "plugin": manifest["name"],
        "version": version,
        "commit": git_output(repo, "rev-parse", "develop"),
        "formal_tag": f"formal/v{version}",
        "config": config,
        "plugin_path": str(plugin),
    }


def _safe_extract(artifact: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(artifact) as archive:
        for info in archive.infolist():
            relative = Path(info.filename)
            if relative.is_absolute() or ".." in relative.parts:
                fail("E_ARCHIVE_PATH", f"unsafe archive member: {info.filename}")
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not info.is_dir():
                destination.write_bytes(archive.read(info))
                destination.chmod((info.external_attr >> 16) & 0o777 or 0o644)


def _replace_tree(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.parent / f".{target.name}.new"
    old = target.parent / f".{target.name}.old"
    if temp.exists():
        shutil.rmtree(temp)
    if old.exists():
        shutil.rmtree(old)
    shutil.copytree(source, temp, symlinks=False)
    if target.exists():
        os.replace(target, old)
    os.replace(temp, target)
    if old.exists():
        shutil.rmtree(old)


def _marketplace(channel: Path, plugin: str, version: str) -> None:
    data = {
        "name": "skill-formal",
        "interface": {"displayName": "Self-authored Skills Formal"},
        "plugins": [
            {
                "name": plugin,
                "source": {"source": "local", "path": f"./plugins/{plugin}"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Developer Tools",
            }
        ],
    }
    existing = channel / ".agents" / "plugins" / "marketplace.json"
    if existing.exists():
        prior = read_json(existing)
        data["plugins"] = [item for item in prior.get("plugins", []) if item.get("name") != plugin] + data["plugins"]
        data["plugins"].sort(key=lambda item: item["name"])
    atomic_json(existing, data)


def _lock(channel: Path) -> dict:
    path = channel / "formal-lock.json"
    return read_json(path) if path.exists() else {"schema_version": 1, "plugins": {}}


def _external_json(command: list[str], code: str) -> dict:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        fail(code, result.stderr.strip() or result.stdout.strip() or repr(command))
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(code, f"non-JSON output from {command[0]}: {exc}")


def _external_run(command: list[str], code: str, *, cwd: Path | None = None) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode:
        fail(code, result.stderr.strip() or result.stdout.strip() or repr(command))


def _activate(channel: Path, plugin: str, version: str) -> None:
    marketplaces = _external_json(
        ["codex", "plugin", "marketplace", "list", "--json"], "E_CODEX_MARKETPLACE_LIST"
    ).get("marketplaces", [])
    selected = next((item for item in marketplaces if item.get("name") == "skill-formal"), None)
    if selected:
        if Path(selected.get("root", "")).resolve() != channel.resolve():
            fail("E_CODEX_MARKETPLACE_CONFLICT", "skill-formal points to a different root")
    else:
        _external_run(
            ["codex", "plugin", "marketplace", "add", str(channel)],
            "E_CODEX_MARKETPLACE_ADD",
        )
    installed = _external_json(["codex", "plugin", "list", "--json"], "E_CODEX_PLUGIN_LIST").get(
        "installed", []
    )
    current = next(
        (item for item in installed if item.get("pluginId") == f"{plugin}@skill-formal"), None
    )
    if current and current.get("version") == version and current.get("enabled") is True:
        return
    _external_run(["codex", "plugin", "add", f"{plugin}@skill-formal", "--json"], "E_CODEX_INSTALL")


def promote(repo: Path, version: str, *, channel: Path | None = None, apply: bool = False, activate: bool = False) -> dict:
    repo = Path(repo).resolve()
    channel = Path(channel or os.environ.get("SKILL_LIFECYCLE_CHANNEL", Path(__file__).parent / "channels" / "formal")).resolve()
    preflight = promotion_preflight(repo, version)
    if not apply:
        return {**preflight, "action": "dry-run", "channel": str(channel)}
    with tempfile.TemporaryDirectory(prefix="skill-lifecycle-") as raw:
        staged = Path(raw) / f"{preflight['plugin']}-{version}.zip"
        built = build_artifact(repo, staged)
        if (
            git_output(repo, "branch", "--show-current") != "develop"
            or git_output(repo, "rev-parse", "develop") != preflight["commit"]
            or git_output(repo, "status", "--porcelain")
        ):
            fail("E_GIT_CHANGED", "repository changed after formal preflight")
        existing_lock = _lock(channel)
        existing_plugin = existing_lock.get("plugins", {}).get(preflight["plugin"], {})
        existing_record = existing_plugin.get("versions", {}).get(version)
        version_dir = channel / "versions" / preflight["plugin"] / version
        formal_tag_commit = (
            git_output(repo, "rev-list", "-n", "1", preflight["formal_tag"])
            if git_output(repo, "tag", "--list", preflight["formal_tag"])
            else ""
        )
        if (
            existing_record
            and existing_record.get("sha256") == built["sha256"]
            and existing_record.get("commit") == preflight["commit"]
            and existing_plugin.get("current_formal") == version
            and formal_tag_commit == preflight["commit"]
            and git_output(repo, "rev-parse", "main") == preflight["commit"]
            and same_tree(version_dir / "payload", channel / "plugins" / preflight["plugin"])
        ):
            return {**preflight, "action": "idempotent", "channel": str(channel), "sha256": built["sha256"]}
        git_run(repo, "switch", "main")
        try:
            git_run(repo, "merge", "--ff-only", preflight["commit"])
            current = git_output(repo, "rev-parse", "HEAD")
            if current != preflight["commit"]:
                fail("E_GIT_COMMIT", "main did not reach the validated develop commit")
            tag_commit = git_output(repo, "rev-list", "-n", "1", preflight["formal_tag"]) if git_output(repo, "tag", "--list", preflight["formal_tag"]) else ""
            if tag_commit and tag_commit != current:
                fail("E_TAG_CONFLICT", f"{preflight['formal_tag']} points to {tag_commit}")
            if not tag_commit:
                git_run(repo, "tag", preflight["formal_tag"], current)
            artifact = version_dir / f"{preflight['plugin']}-{version}.zip"
            if version_dir.exists():
                lock = _lock(channel)
                existing = lock.get("plugins", {}).get(preflight["plugin"], {}).get("versions", {}).get(version)
                if not existing or existing.get("sha256") != built["sha256"]:
                    fail("E_FORMAL_IMMUTABLE", f"formal version already exists with different provenance: {version_dir}")
            else:
                version_dir.mkdir(parents=True)
                shutil.copy2(staged, artifact)
                _safe_extract(artifact, version_dir / "payload")
                (version_dir / f"{preflight['plugin']}-{version}.sha256").write_text(
                    f"{built['sha256']}  {artifact.name}\n", encoding="utf-8"
                )
            _replace_tree(version_dir / "payload", channel / "plugins" / preflight["plugin"])
            lock = _lock(channel)
            plugin_lock = lock.setdefault("plugins", {}).setdefault(
                preflight["plugin"], {"current_formal": version, "versions": {}}
            )
            plugin_lock["current_formal"] = version
            plugin_lock.setdefault("versions", {})[version] = {
                "artifact": str(artifact),
                "commit": current,
                "formal_tag": preflight["formal_tag"],
                "released": plugin_lock.get("versions", {}).get(version, {}).get("released", False),
                "sha256": built["sha256"],
                "promoted_at": datetime.now(timezone.utc).isoformat(),
            }
            atomic_json(channel / "formal-lock.json", lock)
            _marketplace(channel, preflight["plugin"], version)
        finally:
            git_run(repo, "switch", "develop", check=False)
    if activate:
        _activate(channel, preflight["plugin"], version)
    return {**preflight, "action": "applied", "channel": str(channel), "sha256": built["sha256"]}


def _version_record(channel: Path, plugin: str, version: str) -> tuple[dict, dict]:
    lock = _lock(channel)
    try:
        record = lock["plugins"][plugin]["versions"][version]
    except KeyError:
        fail("E_FORMAL_MISSING", f"no formal record for {plugin} {version}")
    artifact = Path(record["artifact"])
    if not artifact.is_file() or sha256_file(artifact) != record["sha256"]:
        fail("E_ARTIFACT_DRIFT", f"artifact does not match formal lock: {artifact}")
    return lock, record


def _verify_existing_release(repo: Path, tag: str, artifact: Path, expected_sha256: str) -> bool:
    viewed = subprocess.run(
        ["gh", "release", "view", tag], cwd=repo, text=True, capture_output=True, check=False
    )
    if viewed.returncode:
        return False
    with tempfile.TemporaryDirectory(prefix="skill-release-verify-") as raw:
        downloaded = Path(raw) / artifact.name
        result = subprocess.run(
            ["gh", "release", "download", tag, "--pattern", artifact.name, "--dir", raw],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode or not downloaded.is_file():
            fail("E_RELEASE_VERIFY", result.stderr.strip() or "released artifact could not be downloaded")
        if sha256_file(downloaded) != expected_sha256:
            fail("E_RELEASE_DRIFT", f"GitHub Release asset differs from formal artifact: {artifact.name}")
    return True


def release(repo: Path, version: str, *, channel: Path | None = None, apply: bool = False) -> dict:
    repo = Path(repo).resolve()
    channel = Path(channel or os.environ.get("SKILL_LIFECYCLE_CHANNEL", Path(__file__).parent / "channels" / "formal")).resolve()
    require_final_semver(version)
    _, _, manifest = load_repo(repo)
    plugin = manifest["name"]
    lock, record = _version_record(channel, plugin, version)
    formal_commit = git_output(repo, "rev-list", "-n", "1", record["formal_tag"])
    if formal_commit != record["commit"]:
        fail("E_FORMAL_TAG", f"{record['formal_tag']} does not match lock commit")
    release_tag = f"v{version}"
    existing_tag = git_output(repo, "tag", "--list", release_tag)
    if existing_tag and git_output(repo, "rev-list", "-n", "1", release_tag) != record["commit"]:
        fail("E_TAG_CONFLICT", f"{release_tag} points to another commit")
    if not apply:
        return {"action": "dry-run", "plugin": plugin, "version": version, "sha256": record["sha256"]}
    artifact = Path(record["artifact"])
    if _verify_existing_release(repo, release_tag, artifact, record["sha256"]):
        if not existing_tag:
            git_run(repo, "tag", release_tag, record["commit"])
        record["released"] = True
        record["released_at"] = record.get("released_at") or datetime.now(timezone.utc).isoformat()
        atomic_json(channel / "formal-lock.json", lock)
        return {"action": "idempotent", "plugin": plugin, "version": version, "sha256": record["sha256"]}
    if not existing_tag:
        git_run(repo, "tag", release_tag, record["commit"])
    git_run(repo, "push", "origin", record["formal_tag"], release_tag)
    checksum = artifact.with_suffix(".sha256")
    if not checksum.exists():
        checksum.write_text(f"{record['sha256']}  {artifact.name}\n", encoding="utf-8")
    _external_run(
        ["gh", "release", "create", release_tag, str(artifact), str(checksum), "--title", release_tag, "--notes", f"Formal {plugin} {version}; SHA-256 {record['sha256']}"],
        "E_GITHUB_RELEASE",
        cwd=repo,
    )
    record["released"] = True
    record["released_at"] = datetime.now(timezone.utc).isoformat()
    atomic_json(channel / "formal-lock.json", lock)
    return {"action": "applied", "plugin": plugin, "version": version, "sha256": record["sha256"]}


def rollback(plugin: str, version: str, *, channel: Path | None = None, apply: bool = False, activate: bool = False) -> dict:
    require_final_semver(version)
    channel = Path(channel or os.environ.get("SKILL_LIFECYCLE_CHANNEL", Path(__file__).parent / "channels" / "formal")).resolve()
    lock, record = _version_record(channel, plugin, version)
    payload = channel / "versions" / plugin / version / "payload"
    if not payload.is_dir():
        fail("E_PAYLOAD_MISSING", f"formal payload is missing: {payload}")
    if not apply:
        return {"action": "dry-run", "plugin": plugin, "version": version, "sha256": record["sha256"]}
    if lock["plugins"][plugin].get("current_formal") == version and same_tree(
        payload, channel / "plugins" / plugin
    ):
        return {"action": "idempotent", "plugin": plugin, "version": version, "sha256": record["sha256"]}
    _replace_tree(payload, channel / "plugins" / plugin)
    lock["plugins"][plugin]["current_formal"] = version
    atomic_json(channel / "formal-lock.json", lock)
    _marketplace(channel, plugin, version)
    if activate:
        _activate(channel, plugin, version)
    return {"action": "applied", "plugin": plugin, "version": version, "sha256": record["sha256"]}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("--root", action="append", type=Path, required=True)
    inspect.add_argument("--json", action="store_true")
    artifact = sub.add_parser("artifact")
    artifact.add_argument("--repo", type=Path, required=True)
    artifact.add_argument("--output", type=Path, required=True)
    for name in ("promote", "release"):
        command = sub.add_parser(name)
        command.add_argument("--repo", type=Path, required=True)
        command.add_argument("--version", required=True)
        command.add_argument("--apply", action="store_true")
    roll = sub.add_parser("rollback")
    roll.add_argument("--plugin", required=True)
    roll.add_argument("--version", required=True)
    roll.add_argument("--apply", action="store_true")
    return root


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_roots(args.root)
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else json.dumps(result, ensure_ascii=False))
            return 0 if result["formal_ready"] else 2
        if args.command == "artifact":
            result = build_artifact(args.repo, args.output)
        elif args.command == "promote":
            result = promote(args.repo, args.version, apply=args.apply, activate=args.apply)
        elif args.command == "release":
            result = release(args.repo, args.version, apply=args.apply)
        else:
            result = rollback(args.plugin, args.version, apply=args.apply, activate=args.apply)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except LifecycleError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
