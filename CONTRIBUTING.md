# Contributing to Ariadne

Contributions should preserve Ariadne's central guarantee: mutable development files, formal runtime bytes, and published release bytes must remain distinguishable and reproducible.

## Development workflow

1. Work on `develop`; keep `main` formal-only.
2. Add or update a failing test before changing runtime behavior.
3. Run `python3 -m unittest discover -s tests -v`.
4. Run a promotion dry-run before proposing a formal version.
5. Do not commit generated formal channels, artifacts, caches, credentials, or local recovery archives.

## AI contribution disclosure

AI assistance must be visible and attributable without replacing the human maintainer's accountability. When Codex materially contributes to a commit, append GitHub's standard trailer after a blank line:

```text
Co-authored-by: Codex <noreply@openai.com>
```

Use the trailer only for commits Codex actually helped produce. The maintainer remains responsible for reviewing, testing, licensing, and publishing the result.

## License

By contributing, you agree that your contribution is licensed under the repository's MIT License.
