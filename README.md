# Ariadne

A standalone Codex Skill that keeps Skill development, formal installation, and public releases from contaminating one another.

Ariadne gives a Skill repository three explicit states and refuses promotion when their identities drift. It uses only the Python standard library at runtime and does not depend on another custom Skill, review agent, CI service, or package manager.

## Why Ariadne

Skill development can silently leak into active agent discovery paths, Plugin caches, release archives, or an old formal installation. A branch name alone does not prevent this. Ariadne combines Git gates, installable-package boundaries, deterministic artifacts, checksums, immutable tags, and dry-run-first mutation commands so each state can be identified and reproduced.

| State | Mutable source | Required identity | Runtime rule |
|---|---|---|---|
| Development | `develop` | working tree and tests | stays outside active Skill discovery |
| Formal | fast-forwarded `main` | `formal/vX.Y.Z`, ZIP, SHA-256, lock | installed through the isolated formal marketplace |
| Release | no rebuild allowed | `vX.Y.Z` on the formal commit | publishes the exact formal ZIP and checksum |

## What it does

- Audits duplicate Skill names, symlinks, branch state, package scope, and discovery paths.
- Packages only the declared Plugin allowlist, excluding tests, notes, generated channels, and repository history.
- Produces deterministic ZIP archives with SHA-256 provenance.
- Promotes `develop` to `main` only through a clean, fast-forward path.
- Releases the already-verified formal artifact instead of rebuilding it.
- Rolls back by selecting a previous immutable formal payload, never by destructive Git reset or cache editing.
- Defaults every mutating operation to dry-run; external writes require `--apply`.

## Requirements

- Codex with Plugin support
- Python 3.10 or newer
- Git
- GitHub CLI only when publishing a GitHub Release

No third-party Python package is required.

## Installation

Register this public repository as a Codex marketplace, then install Ariadne:

```bash
codex plugin marketplace add timshan/ariadne --ref main
codex plugin add ariadne@ariadne
```

Start a new Codex session after installation so Skill discovery is refreshed.

## Quickstart

Ask Codex to invoke the Skill:

```text
Use $ariadne to inspect this Skill repository and classify its current lifecycle state.
```

Or run the bundled controller directly from a checkout:

```bash
python3 lifecycle.py inspect --root PATH --json
python3 lifecycle.py artifact --repo PATH --output PATH
python3 lifecycle.py promote --repo PATH --version X.Y.Z
python3 lifecycle.py promote --repo PATH --version X.Y.Z --apply
python3 lifecycle.py release --repo PATH --version X.Y.Z --apply
python3 lifecycle.py rollback --plugin NAME --version X.Y.Z --apply
```

`promote`, `release`, and `rollback` show their plan unless `--apply` is explicitly supplied. See [the complete runtime policy](plugins/ariadne/skills/ariadne/references/lifecycle-policy.md) before applying a state change.

## Repository contract

A managed repository provides a `lifecycle.json` file:

```json
{
  "plugin_path": "plugins/example",
  "package_paths": [".codex-plugin", "LICENSE", "skills"],
  "discovery_roots": ["~/.codex/skills", "~/.agents/skills"],
  "checks": [["python3", "-m", "unittest", "discover", "-s", "tests", "-v"]]
}
```

`plugin_path` identifies the installable Plugin. `package_paths` is an allowlist relative to that Plugin root. Checks are argument arrays and never pass through a shell.

## Repository layout

```text
.agents/plugins/marketplace.json   public Codex marketplace
plugins/ariadne/                   complete installable Plugin
  .codex-plugin/plugin.json        Plugin identity and version
  lifecycle.py                     standard-library controller
  skills/ariadne/                  self-contained Skill, launcher, and policy
docs/SDD.md                        design, UML, risks, and acceptance criteria
tests/                             lifecycle and packaging tests
lifecycle.json                     this repository's lifecycle contract
lifecycle.py                       maintainer-friendly repository entry point
```

Only `plugins/ariadne/` is installable. Repository documentation, tests, and generated formal state cannot enter the Plugin artifact unless the package contract is intentionally changed.

## Verification

```bash
python3 -m unittest discover -s tests -v
python3 lifecycle.py promote --repo . --version 1.0.0
```

The design and expected behavior are documented in [docs/SDD.md](docs/SDD.md). Contribution rules, including AI contribution disclosure, are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Project contributors

- Tim Shan — maintainer, product direction, review, and release accountability
- OpenAI Codex — AI coding collaborator for design analysis, implementation, tests, and documentation; materially assisted commits use `Co-authored-by: Codex <noreply@openai.com>`

## README references

The information architecture of this README was informed by established Skill projects while the wording and lifecycle design are original to Ariadne:

- [OpenAI Plugins](https://github.com/openai/plugins) — canonical `plugins/<name>` and repository marketplace layout
- [Anthropic Skills](https://github.com/anthropics/skills) — self-contained Skill packaging and explicit testing guidance
- [Superpowers](https://github.com/obra/superpowers) — quickstart, workflow explanation, contents, and contribution structure

## License

Ariadne is released under the [MIT License](LICENSE).
