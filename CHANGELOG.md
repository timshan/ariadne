# Changelog

All notable changes to Ariadne will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and runtime releases follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Repository-only documentation changes are identified explicitly and do not by themselves create a new Plugin release.

## [Unreleased]

## [1.1.2] - 2026-08-11

### Added

- Repository-root changelog baseline for recording unreleased and released Ariadne changes.

### Changed

- README maintenance rule: every subsequent Ariadne change must update this section in the same diff.

### Fixed

- Repeated promotion of an already matching formal version reconciles a requested Codex activation after a prior activation failure without rewriting immutable formal evidence.

### Boundaries

- The changelog baseline itself is repository-only; activation recovery is a Plugin runtime bug fix and advances the development manifest to 1.1.2.
- Activation recovery applies only when artifact, lock, current payload, `main`, and formal tag already match; any provenance conflict remains a hard failure.
- Existing v1.0.0, v1.1.0, and v1.1.1 tags, artifacts, and release notes remain immutable; those releases predate this changelog baseline and are not reconstructed here.

[Unreleased]: https://github.com/timshan/ariadne/compare/v1.1.2...HEAD
[1.1.2]: https://github.com/timshan/ariadne/compare/v1.1.1...v1.1.2
