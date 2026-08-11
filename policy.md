# Self-authored Skill lifecycle policy

The packaged normative runtime copy is `plugins/ariadne/skills/ariadne/references/lifecycle-policy.md`. This repository-level baseline remains concise and testable for maintainers; Ariadne itself carries everything required to operate without another Skill.

This policy is the authority for current and future self-authored Codex Skills. All formal Skills are packaged as Plugins. Ariadne packages its control plane inside its own installable Plugin, while mutable development and generated formal state stay outside active Skill discovery paths.

## Development boundary

- Exactly two permanent source branches exist: `develop` and `main`.
- Feature work and runtime payload changes occur on `develop` in an isolated Codex profile or repository test fixture. A development checkout is not copied into global Skill discovery paths.
- Runtime payload includes `SKILL.md`, `agents/openai.yaml`, scripts, resources, manifest, permissions, dependencies, and packaged files. These changes require SemVer and complete gates.
- Repository-only notes that cannot affect packaged runtime may remain development-only and do not force a release.

## Formal boundary

- `main` contains only validated formal source. Promotion is fast-forward-only from `develop`.
- A formal version uses final strict SemVer, an immutable `formal/vX.Y.Z` tag, a deterministic ZIP, a SHA-256 checksum, and a provenance lock.
- Local execution uses the non-default `skill-formal` marketplace and Codex-managed Plugin cache. Do not edit Plugin caches or copy development Skills into global discovery roots.
- Promotion and rollback are dry-run unless `--apply` is supplied. An Agent may construct or run `--apply` only after explicit user authorization in the current conversation for the exact operation, target, and version. Existing immutable versions may be reused only when bytes and provenance match.

## Release boundary

- A release publishes the exact existing formal artifact. It creates `vX.Y.Z` on the same commit as `formal/vX.Y.Z`, pushes both tags, and attaches the ZIP plus checksum to a GitHub Release.
- Release is an external write and requires explicit user authorization. A changed artifact, tag conflict, or missing lock stops publication.
- Universal directory submission, if ever requested, is a later and separate action.

## Gates and rollback

1. Inspect duplicate Skill names and symlinked payloads.
2. Require a clean `develop` tree, only local `develop` and `main`, and a fast-forward path.
3. Run configured repository checks and Plugin／Skill validators.
4. Build the deterministic artifact and record commit, tags, checksum, and timestamps.
5. For lifecycle, major, or security-boundary changes, obtain w5:p3 adversarial review before first formal use.
6. Roll back by selecting a previous immutable formal version and reinstalling through the formal marketplace. Never use destructive Git reset or edit caches.

Dirty legacy repositories and standalone runtimes are inventory inputs, not overwrite targets. Record path, name, tree hash, Git state, and recovery action before reconciliation; archive rather than delete until the Plugin formal version is proven.
