# Ariadne

Ariadne is a standalone Codex Skill and standard-library control plane that separates mutable Skill development, locally executable formal Plugins, and externally published releases.

It does not require another custom Skill, CI service, package manager, or review agent. The installed Plugin contains `$ariadne`, its complete runtime policy, a launcher, and the controller. Design, risks, acceptance criteria, and UML are in [docs/SDD.md](docs/SDD.md).

## Boundaries

- Development: mutable `develop` source outside active discovery.
- Formal: fast-forwarded `main`, `formal/vX.Y.Z`, deterministic ZIP/SHA-256/lock, and local `skill-formal` installation.
- Release: the exact formal bytes under `vX.Y.Z` and a GitHub Release.

The normative runtime policy is [skills/ariadne/references/lifecycle-policy.md](skills/ariadne/references/lifecycle-policy.md); [policy.md](policy.md) is the repository-level policy baseline.

```bash
python3 lifecycle.py inspect --root PATH --json
python3 lifecycle.py artifact --repo PATH --output PATH
python3 lifecycle.py promote --repo PATH --version X.Y.Z
python3 lifecycle.py promote --repo PATH --version X.Y.Z --apply
python3 lifecycle.py release --repo PATH --version X.Y.Z --apply
python3 lifecycle.py rollback --plugin NAME --version X.Y.Z --apply
python3 -m unittest discover -s tests -v
```

Mutation commands default to dry-run. `promote --apply` and `rollback --apply` activate the selected Plugin through the local `skill-formal` marketplace; `release --apply` performs Git and GitHub external writes.

After formal promotion, open a new Codex session and invoke:

```text
Use $ariadne to classify this Skill change and enforce its lifecycle boundaries.
```
