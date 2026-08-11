import tempfile
import unittest
import os
from pathlib import Path
from unittest import mock

import lifecycle
from helpers import init_repo


class ReleaseTests(unittest.TestCase):
    def fake_gh(self, root: Path, *, release_exists: bool) -> tuple[Path, Path]:
        binary = root / "bin"
        binary.mkdir()
        log = root / "gh.log"
        fake = binary / "gh"
        fake.write_text(
            f"""#!/usr/bin/env python3
import json, os, shutil, sys
args = sys.argv[1:]
with open(os.environ['FAKE_GH_LOG'], 'a', encoding='utf-8') as handle:
    handle.write(json.dumps(args) + '\\n')
if args[:2] == ['release', 'view']:
    raise SystemExit({0 if release_exists else 1})
if args[:2] == ['release', 'download']:
    target = args[args.index('--dir') + 1]
    name = args[args.index('--pattern') + 1]
    shutil.copy2(os.environ['FAKE_GH_ASSET'], os.path.join(target, name))
print(json.dumps({{'ok': True}}))
""",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        return binary, log

    def test_modified_formal_artifact_is_rejected_before_external_call(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            channel = root / "channel"
            lifecycle.promote(repo, "1.0.0", channel=channel, apply=True)
            artifact = next((channel / "versions" / "sample-plugin" / "1.0.0").glob("*.zip"))
            artifact.write_bytes(artifact.read_bytes() + b"drift")
            with self.assertRaisesRegex(lifecycle.LifecycleError, "E_ARTIFACT_DRIFT"):
                lifecycle.release(repo, "1.0.0", channel=channel, apply=False)

    def test_existing_release_with_different_asset_fails_before_tag_or_push(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            channel = root / "channel"
            lifecycle.promote(repo, "1.0.0", channel=channel, apply=True)
            bad_asset = root / "bad.zip"
            bad_asset.write_bytes(b"not the formal artifact")
            binary, log = self.fake_gh(root, release_exists=True)
            with mock.patch.dict(
                os.environ,
                {
                    "PATH": f"{binary}{os.pathsep}{os.environ['PATH']}",
                    "FAKE_GH_LOG": str(log),
                    "FAKE_GH_ASSET": str(bad_asset),
                },
            ):
                with self.assertRaisesRegex(lifecycle.LifecycleError, "E_RELEASE_DRIFT"):
                    lifecycle.release(repo, "1.0.0", channel=channel, apply=True)
            self.assertEqual("", lifecycle.git_output(repo, "tag", "--list", "v1.0.0"))

    def test_new_release_synchronizes_remote_main_and_exact_tags(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            remote = root / "remote.git"
            lifecycle.git_run(root, "init", "--bare", str(remote))
            lifecycle.git_run(repo, "remote", "add", "origin", str(remote))
            lifecycle.git_run(repo, "push", "origin", "main:refs/heads/main")
            stale_remote_main = lifecycle.git_output(remote, "rev-parse", "refs/heads/main")

            (repo / "skills" / "sample" / "SKILL.md").write_text(
                "---\nname: sample-skill\ndescription: Updated fixture.\n---\n\n# Sample\n",
                encoding="utf-8",
            )
            lifecycle.git_run(repo, "add", "skills/sample/SKILL.md")
            lifecycle.git_run(repo, "commit", "-m", "update release payload")
            channel = root / "channel"
            lifecycle.promote(repo, "1.0.0", channel=channel, apply=True)
            formal_commit = lifecycle.git_output(repo, "rev-parse", "formal/v1.0.0")
            self.assertNotEqual(stale_remote_main, formal_commit)

            binary, log = self.fake_gh(root, release_exists=False)
            artifact = next((channel / "versions" / "sample-plugin" / "1.0.0").glob("*.zip"))
            with mock.patch.dict(
                os.environ,
                {
                    "PATH": f"{binary}{os.pathsep}{os.environ['PATH']}",
                    "FAKE_GH_LOG": str(log),
                    "FAKE_GH_ASSET": str(artifact),
                },
            ):
                result = lifecycle.release(repo, "1.0.0", channel=channel, apply=True)
            self.assertEqual(result["action"], "applied")
            self.assertEqual(
                formal_commit,
                lifecycle.git_output(repo, "rev-parse", "v1.0.0"),
            )
            self.assertEqual(formal_commit, lifecycle.git_output(remote, "rev-parse", "refs/heads/main"))
            self.assertEqual(formal_commit, lifecycle.git_output(remote, "rev-parse", "refs/tags/formal/v1.0.0"))
            self.assertEqual(formal_commit, lifecycle.git_output(remote, "rev-parse", "refs/tags/v1.0.0"))
            self.assertIn('"create"', log.read_text(encoding="utf-8"))

    def test_atomic_push_failure_leaves_remote_refs_and_release_unchanged(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            remote = root / "remote.git"
            lifecycle.git_run(root, "init", "--bare", str(remote))
            lifecycle.git_run(repo, "remote", "add", "origin", str(remote))
            lifecycle.git_run(
                repo,
                "push",
                "origin",
                "main:refs/heads/main",
                "main:refs/tags/formal/v1.0.0",
            )
            stale_remote_main = lifecycle.git_output(remote, "rev-parse", "refs/heads/main")

            (repo / "skills" / "sample" / "SKILL.md").write_text(
                "---\nname: sample-skill\ndescription: Updated fixture.\n---\n\n# Sample\n",
                encoding="utf-8",
            )
            lifecycle.git_run(repo, "add", "skills/sample/SKILL.md")
            lifecycle.git_run(repo, "commit", "-m", "update release payload")
            channel = root / "channel"
            lifecycle.promote(repo, "1.0.0", channel=channel, apply=True)

            binary, log = self.fake_gh(root, release_exists=False)
            artifact = next((channel / "versions" / "sample-plugin" / "1.0.0").glob("*.zip"))
            with mock.patch.dict(
                os.environ,
                {
                    "PATH": f"{binary}{os.pathsep}{os.environ['PATH']}",
                    "FAKE_GH_LOG": str(log),
                    "FAKE_GH_ASSET": str(artifact),
                },
            ):
                with self.assertRaisesRegex(lifecycle.LifecycleError, "E_GIT"):
                    lifecycle.release(repo, "1.0.0", channel=channel, apply=True)

            self.assertEqual(stale_remote_main, lifecycle.git_output(remote, "rev-parse", "refs/heads/main"))
            self.assertEqual("", lifecycle.git_output(remote, "tag", "--list", "v1.0.0"))
            self.assertNotIn('"create"', log.read_text(encoding="utf-8"))

    def test_existing_matching_release_repairs_stale_remote_main(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            remote = root / "remote.git"
            lifecycle.git_run(root, "init", "--bare", str(remote))
            lifecycle.git_run(repo, "remote", "add", "origin", str(remote))
            lifecycle.git_run(repo, "push", "origin", "main:refs/heads/main")

            (repo / "skills" / "sample" / "SKILL.md").write_text(
                "---\nname: sample-skill\ndescription: Updated fixture.\n---\n\n# Sample\n",
                encoding="utf-8",
            )
            lifecycle.git_run(repo, "add", "skills/sample/SKILL.md")
            lifecycle.git_run(repo, "commit", "-m", "update release payload")
            channel = root / "channel"
            lifecycle.promote(repo, "1.0.0", channel=channel, apply=True)
            formal_commit = lifecycle.git_output(repo, "rev-parse", "formal/v1.0.0")
            artifact = next((channel / "versions" / "sample-plugin" / "1.0.0").glob("*.zip"))
            binary, log = self.fake_gh(root, release_exists=True)

            with mock.patch.dict(
                os.environ,
                {
                    "PATH": f"{binary}{os.pathsep}{os.environ['PATH']}",
                    "FAKE_GH_LOG": str(log),
                    "FAKE_GH_ASSET": str(artifact),
                },
            ):
                result = lifecycle.release(repo, "1.0.0", channel=channel, apply=True)

            self.assertEqual("idempotent", result["action"])
            self.assertEqual(formal_commit, lifecycle.git_output(remote, "rev-parse", "refs/heads/main"))
            self.assertEqual(formal_commit, lifecycle.git_output(remote, "rev-parse", "refs/tags/formal/v1.0.0"))
            self.assertEqual(formal_commit, lifecycle.git_output(remote, "rev-parse", "refs/tags/v1.0.0"))
            self.assertNotIn('"create"', log.read_text(encoding="utf-8"))

    def test_release_rejects_formal_commit_missing_from_local_main(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = init_repo(root / "repo")
            initial_commit = lifecycle.git_output(repo, "rev-parse", "main")
            remote = root / "remote.git"
            lifecycle.git_run(root, "init", "--bare", str(remote))
            lifecycle.git_run(repo, "remote", "add", "origin", str(remote))
            lifecycle.git_run(repo, "push", "origin", "main:refs/heads/main")

            (repo / "skills" / "sample" / "SKILL.md").write_text(
                "---\nname: sample-skill\ndescription: Updated fixture.\n---\n\n# Sample\n",
                encoding="utf-8",
            )
            lifecycle.git_run(repo, "add", "skills/sample/SKILL.md")
            lifecycle.git_run(repo, "commit", "-m", "update release payload")
            channel = root / "channel"
            lifecycle.promote(repo, "1.0.0", channel=channel, apply=True)
            lifecycle.git_run(repo, "branch", "-f", "main", initial_commit)

            binary, log = self.fake_gh(root, release_exists=False)
            artifact = next((channel / "versions" / "sample-plugin" / "1.0.0").glob("*.zip"))
            with mock.patch.dict(
                os.environ,
                {
                    "PATH": f"{binary}{os.pathsep}{os.environ['PATH']}",
                    "FAKE_GH_LOG": str(log),
                    "FAKE_GH_ASSET": str(artifact),
                },
            ):
                with self.assertRaisesRegex(lifecycle.LifecycleError, "E_RELEASE_MAIN"):
                    lifecycle.release(repo, "1.0.0", channel=channel, apply=True)

            self.assertEqual(initial_commit, lifecycle.git_output(remote, "rev-parse", "refs/heads/main"))
            self.assertEqual("", lifecycle.git_output(remote, "tag", "--list"))
            self.assertNotIn('"create"', log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
