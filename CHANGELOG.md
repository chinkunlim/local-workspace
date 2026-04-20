# Changelog

All notable changes to this project will be documented in this file.
Format: [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH`

---

## [Unreleased]

### Added
- **core**: `task_queue.py` implemented as a single-threaded queue to replace concurrent subprocesses, preventing OOM.
- **core**: `knowledge_pusher.py` to push generated notes to Open WebUI Knowledge API.
- **infra**: `open_claw_tool.py` custom tool for Open WebUI to natively trigger Open Claw pipelines.
- **core**: Obsidian Watchdog added to `inbox_daemon.py` to listen for `status: rewrite` and automatically enqueue files for `note_generator`.

### Changed
- **core**: `inbox_daemon.py` removed legacy HTTP POST to the retired Flask WebUI. Now fully uses local `task_queue.py`.
- **core**: `inbox_daemon.py` now strictly adheres to sandbox input isolation. Removed hardcoded `pdf_routing_rules` that previously bypassed boundaries and wrote directly to cross-skill `output/` directories.
- **skills**: All `temperature` configs in extraction layers (`audio-transcriber`, `doc-parser`) and `smart_highlighter` forcefully set to `0` to prevent hallucinations.
- **skills**: `audio-transcriber` Phase 3 prompt stripped of formatting logic to strictly perform lossless merging.
- **skills**: `note_generator` synthesis map temperature lowered to `0.1` and `0.2` to prevent hallucination during map-reduce.
- **skills**: Purged highlight and synthesis prompts/configs from `audio-transcriber` and `doc-parser` to enforce pure extraction logic.
- **skills**: Migrated and integrated the purged highlighting and Map-Reduce synthesis prompts into `smart_highlighter` and `note_generator`.

---

## [0.9.0] — 2026-04-19

### Added

- `core/inbox_config.json`: 42 configurable PDF routing rules supporting three dispatch modes —
  `audio_ref` (reference-only for audio proofreading), `doc_parser` (full Markdown extraction),
  and `both` (atomic copy to both destinations simultaneously). Rules are hot-reloaded on every
  file event; no daemon restart required.
- `skills/inbox-manager/`: CLI skill exposing `query.py` for runtime inspection and mutation of
  routing rules (`list`, `add <pattern> --routing <mode>`, `remove <pattern>`).
- `skills/__init__.py` and per-package `__init__.py` files: all skill sub-packages are now
  importable as standard Python packages (`from skills.note_generator.scripts.synthesize import …`).
- `watchdog>=4.0.0` and `requests>=2.31.0` declared in `requirements.txt`.
- Subject-folder routing in `inbox_daemon.py`: files placed under `data/raw/<Subject>/` retain
  their subject context propagated through the full pipeline.

### Changed

- `skills/note-generator/` renamed to `skills/note_generator/` — hyphens are invalid Python
  identifiers; underscore convention enforced across all skill package names.
- `skills/smart-highlighter/` renamed to `skills/smart_highlighter/` — same rationale.
- `core/cli_runner.py`, `core/inbox_daemon.py`: bare `from path_builder import PathBuilder`
  replaced with `from core.path_builder import PathBuilder`; `_workspace_root` (not `_core_dir`)
  inserted into `sys.path`, ensuring resolution from any working directory.
- `skills/audio-transcriber/scripts/phases/p05_synthesis.py`: final output corrected from
  `data/raw/` to `data/wiki/<subject>/` — eliminates infinite re-ingestion loop.
- `skills/doc-parser/scripts/phases/p03_synthesis.py`: same correction applied.
- `core/inbox_daemon.py`: API endpoint env var renamed `OPENCLAW_DASHBOARD_URL` →
  `OPENCLAW_API_URL`; default port updated 5001 → 18789.

### Removed

- Flask `core/web_ui/` dashboard (port 5001) — superseded by Open Claw native CLI dispatch and
  Telegram integration. All skill orchestration is now routed through Open Claw's intent engine.
- `flask>=3.0.0` removed from `requirements.txt`.

### Fixed

- `p05_synthesis.py`: restored missing `for` loop body in `run()` (silent `SyntaxError`).
- `p05_synthesis.py`: removed duplicate `_clean_content()` method definition.
- `p04_highlight.py`, `p02_highlight.py`: confirmed delegation to renamed `smart_highlighter`
  package resolves without `ModuleNotFoundError`.

---

## [0.8.0] — 2026-04-19

### Added

- `memory/` AI collaboration layer in `open-claw-sandbox/`
- `infra/` directory consolidating LiteLLM, Open WebUI, Pipelines, and lifecycle scripts
- `.github/` with CI lint workflow and issue/PR templates
- `tests/` directory structure (e2e + integration stubs)
- `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md` at repo root
- `.editorconfig` and `pyproject.toml` at repo root

### Changed

- `pyproject.toml` and `.pre-commit-config.yaml` moved to `open-claw-sandbox/` root
- `CODING_GUIDELINES_FINAL.md` v3.0.0 — merged all prior rules documents

### Removed

- `ops/config/` directory (config files promoted to workspace root)
- `ops/migrate_data_layout.py` (one-off migration script, executed and retired)

---

## [0.1.0] — 2026-04-15

### Added

- Initial `open-claw-sandbox/` sandbox structure
- `core/` shared framework (`PipelineBase`, `PathBuilder`, `StateManager`, `LogManager`, etc.)
- `audio-transcriber` skill — 6-phase MLX-Whisper pipeline
- `doc-parser` skill — 7-phase Docling pipeline
- Inbox Daemon for automatic file routing and pipeline triggering
