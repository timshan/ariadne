---
name: ariadne
description: "Control the lifecycle and independence of self-authored Codex Skills and Plugins so mutable development cannot contaminate formal versions and packaged instructions cannot silently require another custom Skill. Use when creating or changing a Skill, scanning cross-Skill references, proving standalone installation and core checks in an isolated Codex profile, deciding SemVer, promoting develop to main, releasing the exact formal artifact, or rolling back. Operates with its bundled standard-library controller and requires no other Skill."
---

# Ariadne Skill Lifecycle

Keep three states physically and procedurally separate: mutable development source, immutable local formal Plugin, and externally published release. Use the bundled controller; do not replace its gates with manual copying.

## Start every Skill change

1. Locate the source repository and read its `lifecycle.json`, Plugin manifest, current branch, Git status, and configured checks.
2. Classify the requested change as runtime or repository-only. Runtime includes `SKILL.md`, agent metadata, scripts, references, assets, manifests, permissions, dependencies, or any packaged file.
3. Read [the complete lifecycle policy](references/lifecycle-policy.md) before changing branches, versions, discovery paths, formal packages, or release state.
4. Require `independence.standalone_checks` in `lifecycle.json`. Make each command exercise one observable core capability from the installed Plugin payload without calling another custom Skill.
5. Run `python3 <ariadne-skill-directory>/scripts/ariadne.py independence --repo <repo> --json` before promotion. Resolve every reported cross-Skill reference; never satisfy this gate by installing the referenced Skill.
6. Run the controller from any working directory with `python3 <ariadne-skill-directory>/scripts/ariadne.py ...`. Mutation commands are dry-run unless `--apply` is explicit.

## Mutation authorization

- Never construct or run `--apply` from inferred intent, standing policy, or a broad earlier approval.
- Require explicit user authorization in the current conversation for the exact operation, repository or Plugin, version, and external target when one exists.
- If that authorization is absent, complete only the dry-run, report the proposed mutation, and ask one concise confirmation question.

## Development boundary

- Keep exactly two permanent local branches: `develop` and `main`. Make runtime changes only on `develop`; do not create feature branches or worktrees as part of this workflow.
- Keep development source outside Codex Skill discovery roots and Plugin cache. Test it through an isolated profile, explicit file path, or repository checks.
- Add tests before implementation for changed gates. Preserve dirty trees and legacy runtimes as separate evidence; never reconcile by blind overwrite.
- Do not instruct the packaged Skill to invoke a dollar-prefixed external Skill name, name a discovered external Skill as a required step, or read another Skill directory. Bundle required policy, scripts, references, and assets inside the target Plugin.
- A repository managed by Ariadne must provide `lifecycle.json` with `plugin_path`, argument-array `checks`, non-empty argument-array `independence.standalone_checks`, and real `discovery_roots`. When generated state or repository-only files live under the Plugin root, define explicit `package_paths` so they cannot enter inspection or artifacts.

## Formal boundary

1. Run `python3 <ariadne-skill-directory>/scripts/ariadne.py inspect --root <discovery-root> --json`; any duplicate Skill name or symlink fails the formal gate.
2. Run the independence gate. It scans and hashes exact package files, runs repository checks, rejects payload drift, re-scans unchanged bytes, then installs the bound allowlisted artifact as the sole enabled Plugin under temporary empty user/Codex directories. Codex and standalone checks use resolved absolute executables and a minimal non-inherited environment.
3. Set a final strict SemVer in `.codex-plugin/plugin.json`; prerelease or build metadata is not a formal version.
4. Run `.../ariadne.py promote --repo <repo> --version X.Y.Z` and inspect the dry-run result.
5. Use `--apply` only after the mutation authorization rule, a clean `develop`, passing checks, fast-forward ancestry, recovery evidence, and any required review. Promotion fast-forwards `main` to the validated commit, creates `formal/vX.Y.Z`, records a deterministic ZIP SHA-256 and lock under `~/.local/share/ariadne/formal`, and installs through the non-default `skill-formal` marketplace. If those formal bytes and refs already match after an activation failure, repeating the exact authorized promotion retries only idempotent activation and does not rewrite formal evidence.
6. Validate the extracted formal Plugin and Skill, then start a new Codex session to test discovery. Do not edit the installed cache.

## Release boundary

- Release only the existing formal artifact. Run `.../ariadne.py release --repo <repo> --version X.Y.Z` first; `--apply` is a separate authorized external write.
- `vX.Y.Z` and `formal/vX.Y.Z` must point to the same commit. A GitHub Release must contain the exact locked ZIP and checksum; a pre-existing release asset is downloaded and hashed before it is accepted.
- The apply path must atomically synchronize local `main` and both exact tags to `origin` before creating the GitHub Release. Do not force a ref or continue after an atomic push failure.
- Push or publish only after checking remote state to prevent duplicate external writes.

## Rollback and stopping rules

- Run `.../ariadne.py rollback --plugin <name> --version X.Y.Z` first, then add `--apply` only for a verified immutable version. Rollback switches the formal channel and reinstalls; it does not reset Git or modify cache files.
- Stop without mutation on dirty or divergent Git state, a third local branch, duplicate or symlink discovery, cross-Skill reference, malformed independence contract, isolated install/identity/check failure, failed or payload-mutating repository check, changed repository after preflight, standalone/formal artifact drift, tag conflict, marketplace conflict, or unavailable recovery evidence.
- Report exact version, commit, formal tag, artifact SHA-256, installed Plugin identity, and any remaining legacy copy at handoff.

## Independence contract

Ariadne's required runtime is only this Plugin, Python 3 standard library, Git, and the Codex CLI. GitHub CLI is needed only for external release. Other Skills, review agents, CI services, package managers, and network access are optional policy inputs, never runtime prerequisites.

The static gate detects explicit Skill identifiers and known discovered names; it cannot prove that unattributed prose or logic was never copied. Report that provenance limit separately from the hard standalone-install result.
