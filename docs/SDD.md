---
change_id: SKILL-LIFECYCLE-001
title: Skill development, formal, and release lifecycle control
risk_tier: high-risk
status: verification-ready
owner: Tim Shan
contributors: Tim Shan; OpenAI Codex
date: 2026-08-11
tier_rationale: Changes Git branches, local Codex runtime packages, immutable artifacts, and external GitHub releases; a faulty transition can activate unreviewed instructions or lose rollback provenance.
affected_paths: D:\project\ariadne
review_owner: w5:p3 Claude Code for the standalone lifecycle and publication boundary
recovery: Preserve hashes and Git refs before mutation; retain legacy runtime copies outside discovery paths; reinstall the previous immutable formal artifact.
---

# Skill development, formal, and release lifecycle control

## Goal and non-goals

Goal: provide one deterministic, auditable, standalone Ariadne Skill and bundled control plane that keeps mutable Skill development, locally executable formal versions, and externally published releases from being discovered or modified as if they were the same version, even when no other custom Skill is installed.

Non-goals:

- Do not replace Git, Codex Plugin validation, Skill validation, or human authorization.
- Do not introduce CI, mandatory PRs, automatic dependency installation, telemetry, or automatic external publishing.
- Do not overwrite managed repositories or current standalone Skills during inventory.
- Do not treat repository-only documentation changes as Plugin runtime releases.

## Current state and expected outcomes

Current:

- The installable Plugin is physically isolated at `plugins/ariadne/`; tests and repository documents are outside its package root.
- The Plugin contains its Skill, complete runtime policy, launcher, controller, manifest, and MIT license.
- The repository marketplace points only to the installable Plugin directory.
- The controller uses the Python standard library and records installed commit and artifact checksum in a formal lock.

| Outcome ID | Observable expected result | Threshold or evidence |
|---|---|---|
| OUT-001 | Development payload is isolated | Duplicate-name and symlink audit returns zero for a formal session. |
| OUT-002 | Formal promotion is reproducible | Version, commit, formal tag, deterministic ZIP SHA-256, and installed source agree. |
| OUT-003 | Release cannot drift from formal | Release command rejects any byte or provenance mismatch. |
| OUT-004 | Existing runtime remains recoverable | Legacy inventory contains path, Skill name, hash, source state, and recovery action before migration. |
| OUT-005 | Personal workflow stays light | Python standard library only; mutation requires `--apply`; no CI or service dependency. |
| OUT-006 | Lifecycle control works as an independent Skill | An isolated Codex profile containing only the Ariadne Plugin discovers `$ariadne`, and its bundled launcher exposes all controller commands. |

## Requirements

- REQ-001: Keep exactly two permanent source branches, `develop` and `main`; ordinary work occurs only on `develop`, and normal promotion to `main` must be fast-forward-only.
- REQ-002: Treat changes to `SKILL.md`, `agents/openai.yaml`, bundled resources, scripts, Plugin manifest, permissions, dependencies, or package payload as runtime changes requiring SemVer and the full lifecycle.
- REQ-003: Discover duplicate Skill names and symlinked Skill or Plugin payloads across configured roots and fail the formal gate.
- REQ-004: Validate strict SemVer and distinguish development prereleases from final formal versions.
- REQ-005: Build deterministic, sorted, symlink-free ZIP artifacts and record SHA-256, source commit, Plugin name, version, formal tag, and timestamp in a lock.
- REQ-006: Default `promote`, `release`, and `rollback` to dry-run; require explicit `--apply` and verify idempotency before mutation.
- REQ-007: Publish only an existing formal artifact whose checksum and commit match the lock and `formal/vX.Y.Z` tag; create `vX.Y.Z` on the same commit.
- REQ-008: Roll back by restoring a previous immutable formal package into the marketplace channel and reinstalling it, never by editing Plugin cache or destructive Git reset.
- REQ-009: Preserve dirty repositories and legacy runtimes during inventory; no reconciliation or removal occurs without comparison, tests, and a recovery copy.
- REQ-010: Package all lifecycle authority inside Ariadne while keeping repository-only development material outside the installable Plugin.
- REQ-011: Package the complete policy, launcher, and standard-library controller as the `ariadne` Plugin/Skill without any runtime dependency on another Skill, review agent, CI service, or package manager.

## Acceptance criteria

- AC-001 (REQ-001): Given a dirty tree, wrong branch, divergent `main`, or third permanent branch, when formal preflight runs, then it exits nonzero with a stable diagnostic and makes no change.
- AC-002 (REQ-002, REQ-004): Given a runtime payload change without a final strict SemVer, when promotion runs, then it fails; a repository-only documentation change does not force a Plugin release.
- AC-003 (REQ-003): Given two discovered `SKILL.md` files with the same frontmatter name or any symlinked payload, when inspect runs, then it identifies every path and fails the formal gate.
- AC-004 (REQ-005): Given the same clean Plugin tree and commit, when two artifacts are built, then their bytes and SHA-256 are identical.
- AC-005 (REQ-006): Given a valid promotion without `--apply`, when the command completes, then Git refs, channel files, lock, runtime, and external state remain unchanged.
- AC-006 (REQ-005, REQ-007): Given a formal artifact modified after promotion, when release runs, then it stops before tag creation or GitHub mutation.
- AC-007 (REQ-008): Given two formal versions, when rollback selects the older version, then the current marketplace payload and lock point to the older checksum while immutable version directories remain unchanged.
- AC-008 (REQ-009): Given a dirty repository and a differing standalone runtime, when inventory runs, then both are recorded separately and neither is copied over the other.
- AC-009 (REQ-010): Given only the packaged Ariadne Plugin, when Codex invokes `$ariadne`, then the complete policy and controller remain available without repository-only files or another Skill.
- AC-010 (REQ-011): Given an isolated Codex profile with only Ariadne installed, when Plugin discovery and the bundled launcher are invoked, then `$ariadne` is available and `inspect`, `artifact`, `promote`, `release`, and `rollback` commands work without another Skill.

## Constraints, assumptions, and unknowns

- Constraint: Use Python 3 standard library and Git/Codex/GitHub CLIs already present; execute subprocesses without `shell=True`.
- Constraint: Use `rg` for active text and file searches; do not add another search implementation to user-facing runbooks.
- Constraint: Do not store credentials, tokens, or authenticated repository URLs in locks, logs, artifacts, or errors.
- Assumption: Plugin payload lives at a repository-relative path declared in `lifecycle.json`, normally the repository root for a Plugin or a specified Plugin subdirectory.
- Assumption: A non-default local marketplace rooted at `~/.local/share/ariadne/formal` is explicitly configured once; formal installs use its managed cache rather than direct standalone copies.
- Unknown: GitHub universal Plugin directory submission policy may change; v1 release stops at Git tag, GitHub Release, checksum, and optional later submission.

## Options and decision

| Option | Benefit | Cost or risk | Decision |
|---|---|---|---|
| Standalone copies plus manual Git tags | Small initial change | No Plugin version field; direct-copy drift and duplicate discovery remain | Reject |
| Full semantic-release/CI pipeline | Mature release state machine | Node/CI/dependency and credential scope exceeds personal need | Reject |
| Python controller adapting Codex Plugin layout | Deterministic, inspectable, WSL-compatible, minimal dependencies | Small local tool must be maintained and tested | Select |

## Design and contracts

The control project exposes these stable commands:

```text
python3 lifecycle.py inspect [--root PATH ...] [--json]
python3 lifecycle.py artifact --repo PATH --output PATH
python3 lifecycle.py promote --repo PATH --version X.Y.Z [--apply]
python3 lifecycle.py release --repo PATH --version X.Y.Z [--apply]
python3 lifecycle.py rollback --plugin NAME --version X.Y.Z [--apply]
```

Each managed repository provides `lifecycle.json` with `plugin_path`, optional `package_paths` allowlist, `checks` as argument arrays, and discovery roots. Generated formal state is outside source at `~/.local/share/ariadne/formal`. The formal lock contains only non-secret provenance:

```json
{
  "plugins": {
    "example": {
      "current_formal": "1.0.0",
      "versions": {
        "1.0.0": {
          "commit": "...",
          "formal_tag": "formal/v1.0.0",
          "artifact": "...zip",
          "sha256": "...",
          "released": false
        }
      }
    }
  }
}
```

All JSON writes use a temporary sibling followed by `os.replace`. Errors name paths and stable codes but redact URL userinfo.

## Necessary UML

decision_question: Where must mutable source, immutable formal payloads, runtime cache, and public release be separated?
traces: REQ-003, REQ-005, REQ-007, AC-003, AC-004, AC-006

~~~mermaid
flowchart LR
    Dev[develop branch\nmutable source] -->|validated fast-forward| Main[main + formal tag]
    Main --> Builder[deterministic artifact builder]
    Builder --> Versions[formal/versions\nimmutable payload + SHA-256]
    Versions --> Current[formal marketplace current copy]
    Current --> Cache[Codex managed plugin cache]
    Cache --> Ariadne[Ariadne Skill + bundled launcher]
    Versions -->|same bytes only| Release[Git tag + GitHub Release]
~~~

decision_question: Which transitions are legal, and where must a failed or repeated operation stop?
traces: REQ-001, REQ-006, REQ-008, AC-001, AC-005, AC-007

~~~mermaid
stateDiagram-v2
    [*] --> Development
    Development --> FormalPreflight: promote dry-run
    FormalPreflight --> Development: gate fails / no mutation
    FormalPreflight --> Formal: --apply + all gates pass
    Formal --> Released: exact artifact + explicit --apply
    Formal --> Formal: idempotent repeat
    Released --> Released: idempotent repeat
    Formal --> PreviousFormal: rollback --apply
    Released --> PreviousFormal: rollback --apply
~~~

no_diagram_rationale: Not applicable; component ownership and lifecycle transitions materially determine whether development content can contaminate runtime.

## Threat, trust, data, and abuse cases

- Trust boundary: repository and Plugin contents are executable instructions; marketplace and runtime cache are separate mutation boundaries; GitHub is an external boundary.
- Sensitive data or secret handling: never read or serialize tokens; invoke `gh` without exposing authentication; redact URL userinfo in diagnostics.
- Abuse case and control: malicious paths, symlinks, `..`, duplicate names, dirty trees, moving tags, modified artifacts, and repeated external writes must be rejected before mutation.
- Abuse case and control: configuration commands are arrays executed without a shell; configuration is accepted only from the explicitly selected repository.

## Failure, security, and observability

| Failure or risk | Detection threshold | Handling or recovery |
|---|---|---|
| Duplicate or symlinked Skill | Any occurrence | Fail inspect and promotion; list paths; do not delete automatically. |
| Dirty or divergent Git state | Any tracked/untracked change or non-FF promotion | Fail before branch or tag mutation. |
| Artifact drift | SHA-256 mismatch | Stop release/rollback and retain current runtime. |
| Partial file update | Temp write/rename failure | Leave prior target intact and report stable error. |
| Repeated push/release | Existing matching tag/release | Return idempotent success; conflicting target fails. |
| Secret-bearing URL in error | URL userinfo detected | Redact before output or persistence. |

## Migration and reconciliation

- Backup or restore point: record SHA-256 and Git status for all existing runtime and source trees; use a dated recovery archive outside discovery roots before disabling anything.
- Rehearsal: use temporary Git repositories and an isolated Codex profile to exercise Plugin conversion, formal promotion, local installation, release, and rollback checks.
- Reconciliation: classify an existing standalone runtime as legacy formal and its mutable repository as development; compare behavior and tests before choosing a new Plugin formal version.
- Irreversible boundary: deletion of legacy copies and public release creation are separate explicit actions; initial migration disables or archives rather than deletes.

## Test portfolio and TDD slices

Outer acceptance or contract oracle: subprocess CLI tests over temporary Git repositories, Plugin trees, discovery roots, marketplace channels, and fake `gh`/`codex` executables.

1. RED: Add failing SemVer, duplicate, symlink, deterministic artifact, dry-run, drift, idempotency, rollback, and legacy-preservation tests before implementation.
2. GREEN: Implement the smallest standard-library modules and CLI behavior to satisfy one vertical transition at a time.
3. REFACTOR: Separate filesystem, Git, artifact, lock, and external command adapters while preserving subprocess-level contracts.
4. CHECK: Run unit/CLI tests, Plugin and Skill validators, isolated install tests, source integrity checks, and independent review.

Special evidence: migration rehearsal, source/runtime hash comparison, tag/artifact checksum match, duplicate discovery audit, redacted error test, and w5:p3 report.

## Traceability

| Requirement | Acceptance | Test | Implementation | Evidence |
|---|---|---|---|---|
| REQ-001 | AC-001 | tests/test_git_gates.py | lifecycle.py Git adapter | Pass |
| REQ-002, REQ-004 | AC-002 | tests/test_versioning.py | lifecycle.py manifest/version checks | Pass |
| REQ-003 | AC-003 | tests/test_inspect.py | lifecycle.py discovery audit | Pass |
| REQ-005 | AC-004 | tests/test_artifact.py | lifecycle.py deterministic ZIP and lock | Pass |
| REQ-006 | AC-005 | tests/test_dry_run.py | lifecycle.py apply boundary | Pass |
| REQ-007 | AC-006 | tests/test_release.py | lifecycle.py release verifier | Pass |
| REQ-008 | AC-007 | tests/test_rollback.py | lifecycle.py channel switch | Pass |
| REQ-009 | AC-008 | tests/test_inventory.py | lifecycle.py inventory | Pass |
| REQ-010 | AC-009 | tests/test_policy_contract.py and tests/test_ariadne_skill.py | packaged policy and Plugin boundary | Pass |
| REQ-011 | AC-010 | tests/test_ariadne_skill.py and isolated profile acceptance | plugins/ariadne/.codex-plugin/plugin.json, plugins/ariadne/skills/ariadne, plugins/ariadne/lifecycle.py | 27-test suite and Plugin/Skill validators pass; final nested-layout isolated acceptance is pending. |

## Staged rollout, monitoring, and rollback

- Stage and stop condition: controller unit tests → temporary-repository acceptance → isolated Codex install → adversarial review → formal promotion → public repository and release. Stop on any checksum, duplicate, source-integrity, or review failure.
- Monitoring and threshold: every formal action records exact version/commit/hash; any mismatch is a hard failure. `codex plugin list` must show one intended formal version before standalone disablement.
- Rollback trigger and command or procedure: trigger on activation failure, unexpected duplicate, behavior regression, checksum mismatch, or review rejection; restore previous channel payload and reinstall, leaving source refs unchanged.
- Independent review or approval boundary: w5:p3 PASS is required before first formal use of the controller and for new/major/security-boundary migrations; user authorization is required for installation, push, tag, GitHub Release, and legacy removal.

## Verification evidence

- RED evidence: the repository-marketplace test failed before `plugins/ariadne/` and its marketplace existed.
- GREEN evidence: 27 unit and subprocess tests pass after the package-boundary refactor.
- Refactor or exception: repository entry point delegates to the single packaged controller; no second controller implementation is maintained.
- Fresh verification: Plugin and Skill validators pass on `plugins/ariadne/`.
- Realistic outcome check: the prior root-layout build passed isolated installation; the final nested marketplace layout requires one fresh isolated install before promotion.
- Security／performance／migration evidence: symlink, path traversal, URL redaction, dirty-tree, duplicate-name, artifact drift, and idempotency tests pass.
- Remaining risks: GitHub universal directory submission remains outside v1; public installation commands require verification after repository creation.
