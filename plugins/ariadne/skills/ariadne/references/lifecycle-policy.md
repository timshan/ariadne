# Ariadne lifecycle policy

This is the normative runtime policy for current and future self-authored Codex Skills. Formal Skills are Plugins; mutable source is never a runtime installation.

## State boundaries

### Development

- Source branch: `develop`.
- Version: may be incomplete or prerelease, but it cannot be installed as formal.
- Location: repository or isolated test profile outside active Skill discovery and Plugin cache.
- Allowed actions: design, tests, implementation, validators, inventory, dry-run, and reversible recovery snapshots.
- Forbidden actions: manual copy to global discovery, direct cache edit, formal tag, public release, or claiming development bytes are formal.

### Formal

- Source branch: `main`, reached by fast-forward-only promotion of an exact validated `develop` commit.
- Version: final strict `X.Y.Z` SemVer.
- Identity: `formal/vX.Y.Z`, deterministic ZIP, SHA-256, source commit, and formal lock must agree.
- Location: immutable version directory plus a generated non-default `skill-formal` marketplace; Codex installs into its managed cache.
- Required gates: clean tree, only `develop` and `main`, duplicate/symlink-free discovery, configured checks, manifest/version match, and preserved rollback evidence.

### Release

- Source: the existing formal ZIP only; never rebuild for publication.
- Identity: `vX.Y.Z` points to the same commit as `formal/vX.Y.Z`.
- External state: branch/tag push and GitHub Release are separately authorized and checked against remote state before writing.
- Assets: ZIP and `.sha256`; downloaded release bytes must reproduce the locked SHA-256.

## Runtime-change rule

A change is runtime-affecting when it alters a Skill, agent metadata, scripts, references, assets, Plugin manifest, permissions, dependencies, configuration consumed by the Plugin, or any packaged file. Runtime changes require a new SemVer and the full lifecycle. Documentation outside the package that cannot affect runtime may remain repository-only.

## Repository contract

Each managed repository contains `lifecycle.json`:

```json
{
  "plugin_path": "plugins/example",
  "package_paths": [".codex-plugin", "LICENSE", "lifecycle.py", "skills"],
  "discovery_roots": ["~/.codex/skills", "~/.agents/skills"],
  "checks": [["python3", "-m", "unittest", "discover", "-s", "tests", "-v"]]
}
```

Commands are argument arrays and never pass through a shell. Paths may be repository-relative or explicit user discovery roots. Do not include secrets, authenticated URLs, or commands that install dependencies or mutate external state as checks.

`package_paths` is an allowlist relative to the Plugin root. Use it whenever ignored generated state, tests, recovery archives, or repository-only documentation share that root. Ariadne's default formal channel is `~/.local/share/ariadne/formal`; `ARIADNE_FORMAL_CHANNEL` may select another explicit location outside source and discovery paths.

## Formal gate

Promotion must stop before mutation for any of these conditions:

- dirty or detached source, current branch other than `develop`, third local branch, or non-fast-forward ancestry;
- manifest name/version error, prerelease/build metadata, duplicate Skill name, symlink, path escape, or failed repository check;
- source changed after preflight, existing formal version with different bytes/provenance, or conflicting tag;
- missing recovery evidence when a legacy or dirty runtime is being replaced.

All file locks use atomic replacement. Artifacts use sorted paths, fixed timestamps, normalized modes, no symlinks, and safe extraction that rejects absolute and parent paths.

## Mutation authorization gate

Dry-run is always allowed. Before an Agent constructs or runs any `--apply` command, the current conversation must contain explicit user authorization for the exact operation, repository or Plugin, version, and external target when one exists. Standing policy, inferred intent, or broad prior approval is insufficient. Without that authorization, the Agent stops after reporting the dry-run plan and asks one concise confirmation question.

## Activation, release, and rollback

- Activation checks configured marketplaces and installed Plugins using structured Codex JSON. A same-name marketplace pointing elsewhere is a conflict.
- Release checks the formal lock and tag before any GitHub write. Existing releases are downloaded and hashed. New releases push only the exact formal/release tags and attach the locked artifact plus checksum.
- Rollback selects an earlier immutable formal payload, verifies its checksum, atomically switches the current marketplace payload, and reinstalls it. It never performs destructive Git reset or cache editing.

## Recovery and evidence

Before replacing legacy or dirty content, record path, Skill name, tree hash, Git state, archive/diff location, restoration procedure, and non-secret checksum. Archive or move legacy runtimes outside discovery before formal promotion; do not delete them until the user separately chooses retirement.

The handoff evidence is: version, commit, branch set, formal tag, artifact path/hash, formal lock, validator/test results, installed Plugin ID/version/enabled state, release URL/hash when applicable, and remaining legacy locations.
