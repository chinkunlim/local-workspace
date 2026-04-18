# Changelog

All notable changes to this project will be documented in this file.
Format: [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH`

---

## [Unreleased]

### Added
- `memory/` AI collaboration layer in `open-claw-workspace/`
- `infra/` directory consolidating LiteLLM, Open WebUI, Pipelines, and lifecycle scripts
- `.github/` with CI lint workflow and issue/PR templates
- `tests/` directory structure (e2e + integration stubs)
- `docs/api/`, `docs/architecture/`, `docs/guides/` subdirectories
- `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md` at repo root
- `.editorconfig` and `pyproject.toml` at repo root

### Changed
- `pyproject.toml` and `.pre-commit-config.yaml` moved to `open-claw-workspace/` root
- `CODING_GUIDELINES_FINAL.md` v3.0.0 — merged all prior rules documents

### Removed
- `ops/config/` directory (config files promoted to workspace root)
- `ops/migrate_data_layout.py` (one-off script, executed and complete)

---

## [0.1.0] — 2026-04-15

### Added
- Initial `open-claw-workspace/` sandbox structure
- `core/` shared framework (PipelineBase, PathBuilder, StateManager, LogManager, etc.)
- `voice-memo` skill — 6-phase MLX-Whisper pipeline
- `pdf-knowledge` skill — 7-phase Docling pipeline
- Central Dashboard (Flask, port 5001)
- Inbox Daemon for automatic file processing
