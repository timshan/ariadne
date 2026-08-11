---
name: ariadne
description: "Control the lifecycle of self-authored Codex Skills and Plugins so mutable development cannot contaminate locally executable formal versions or externally published releases. Use when creating or changing a Skill, deciding whether a change requires SemVer, auditing duplicate Skill discovery, promoting develop to main, building or installing a formal Plugin, releasing the exact formal artifact, or rolling back. Operates independently with its bundled standard-library controller and does not require any other Skill."
---

# Ariadne Skill Lifecycle

Keep three states physically and procedurally separate: mutable development source, immutable local formal Plugin, and externally published release. Use the bundled controller; do not replace its gates with manual copying.

## Start every Skill change

1. Locate the source repository and read its `lifecycle.json`, Plugin manifest, current branch, Git status, and configured checks.
2. Classify the requested change as runtime or repository-only. Runtime includes `SKILL.md`, agent metadata, scripts, references, assets, manifests, permissions, dependencies, or any packaged file.
3. Read [the complete lifecycle policy](references/lifecycle-policy.md) before changing branches, versions, discovery paths, formal packages, or release state.
4. Run the controller from any working directory with `python3 <ariadne-skill-directory>/scripts/ariadne.py ...`. Mutation commands are dry-run unless `--apply` is explicit.

## Development boundary

- Keep exactly two permanent local branches: `develop` and `main`. Make runtime changes only on `develop`; do not create feature branches or worktrees as part of this workflow.
- Keep development source outside Codex Skill discovery roots and Plugin cache. Test it through an isolated profile, explicit file path, or repository checks.
- Add tests before implementation for changed gates. Preserve dirty trees and legacy runtimes as separate evidence; never reconcile by blind overwrite.
- A repository managed by Ariadne must provide `lifecycle.json` with `plugin_path`, argument-array `checks`, and real standalone `discovery_roots`.

## Formal boundary

1. Run `python3 <ariadne-skill-directory>/scripts/ariadne.py inspect --root <discovery-root> --json`; any duplicate Skill name or symlink fails the formal gate.
2. Set a final strict SemVer in `.codex-plugin/plugin.json`; prerelease or build metadata is not a formal version.
3. Run `.../ariadne.py promote --repo <repo> --version X.Y.Z` and inspect the dry-run result.
4. Use `--apply` only after a clean `develop`, passing checks, fast-forward ancestry, recovery evidence, and any required review. Promotion fast-forwards `main` to the validated commit, creates `formal/vX.Y.Z`, records a deterministic ZIP SHA-256 and lock, and installs through the non-default `skill-formal` marketplace.
5. Validate the extracted formal Plugin and Skill, then start a new Codex session to test discovery. Do not edit the installed cache.

## Release boundary

- Release only the existing formal artifact. Run `.../ariadne.py release --repo <repo> --version X.Y.Z` first; `--apply` is a separate authorized external write.
- `vX.Y.Z` and `formal/vX.Y.Z` must point to the same commit. A GitHub Release must contain the exact locked ZIP and checksum; a pre-existing release asset is downloaded and hashed before it is accepted.
- Push or publish only after checking remote state to prevent duplicate external writes.

## Rollback and stopping rules

- Run `.../ariadne.py rollback --plugin <name> --version X.Y.Z` first, then add `--apply` only for a verified immutable version. Rollback switches the formal channel and reinstalls; it does not reset Git or modify cache files.
- Stop without mutation on dirty or divergent Git state, a third local branch, duplicate or symlink discovery, failed check, changed repository after preflight, artifact drift, tag conflict, marketplace conflict, or unavailable recovery evidence.
- Report exact version, commit, formal tag, artifact SHA-256, installed Plugin identity, and any remaining legacy copy at handoff.

## Independence contract

Ariadne's required runtime is only this Plugin, Python 3 standard library, Git, and the Codex CLI. GitHub CLI is needed only for external release. Other Skills, review agents, CI services, package managers, and network access are optional policy inputs, never runtime prerequisites.
