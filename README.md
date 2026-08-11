# Skill lifecycle control

This standard-library Python control plane separates mutable development, locally executable formal Plugins, and externally published releases for self-authored Codex Skills.

The normative rules are in [policy.md](policy.md); design, risks, acceptance criteria, and UML are in [docs/SDD.md](docs/SDD.md).

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
