# Changelog

All notable changes to this project will be documented in this file.
Format: [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH`

> [!NOTE]
> **Historical Archival:** For the granular, step-by-step AI execution logs, implementation plans, and walkthroughs of these changes, please refer to the master index at **[`memory/HISTORY.md`](memory/HISTORY.md)**.

---

## [9.2.0] — 2026-05-05

### Added
- **docs**: Established a formal `identity/` directory for global persona configuration.
- **docs**: Created `OPENCLAW_TECH_STACK.md` as an exhaustive reference for the project's security defenses, multi-agent architecture, DAG states, and advanced Python implementations. Linked in `INDEX.md` and `STRUCTURE.md`.

### Changed
- **docs**: Executed a comprehensive restructure of the documentation system based on the `doc_system_template.md`. `ARCHITECTURE.md` was moved to the global `docs/` folder, while all files in `memory/` were explicitly reformatted with strict boilerplate headers to ensure AI memory persistence without historical loss.
- **core**: `task_queue.py` implemented as a single-threaded queue to replace concurrent subprocesses, preventing OOM.
- **core**: `knowledge_pusher.py` to push generated notes to Open WebUI Knowledge API.
- **infra**: `open_claw_tool.py` custom tool for Open WebUI to natively trigger Open Claw pipelines.
- **core**: Obsidian Watchdog added to `inbox_daemon.py` to listen for `status: rewrite` and automatically enqueue files for `note_generator`.
- **skills**: Added deterministic chunk-level `tqdm` progress bars in `audio_transcriber` Phase 1 when falling back to 30s chunks, to provide clear visual feedback during long transcribing operations.

### Changed
- **core**: Fixed Path Traversal Defense and `WORKSPACE_DIR` resolution logic in `bootstrap.py`, `pipeline_base.py`, and `atomic_writer.py`. Resolved `PermissionError` and `ConfigValidationError` when launching scripts from subdirectories without environment variables.
- **core**: `inbox_daemon.py` removed legacy HTTP POST to the retired Flask WebUI. Now fully uses local `task_queue.py`.
- **core**: `inbox_daemon.py` now strictly adheres to sandbox input isolation. Removed hardcoded `pdf_routing_rules` that previously bypassed boundaries and wrote directly to cross-skill `output/` directories.
- **skills**: Fixed `ZeroDivisionError` in `audio_transcriber` Phase 1 repetition detection (`detect_repetition`) caused by empty audio segments.
- **skills**: Suppressed internal `tqdm` outputs and stdout/stderr chatters of `mlx-whisper` inside loops to maintain a clean "Quiet Pipeline" CLI interface.
- **skills**: All `temperature` configs in extraction layers (`audio_transcriber`, `doc_parser`) and `smart_highlighter` forcefully set to `0` to prevent hallucinations.
- **skills**: `audio_transcriber` Phase 3 prompt stripped of formatting logic to strictly perform lossless merging.
- **skills**: `note_generator` synthesis map temperature lowered to `0.1` and `0.2` to prevent hallucination during map-reduce.
- **skills**: Purged highlight and synthesis prompts/configs from `audio_transcriber` and `doc_parser` to enforce pure extraction logic.
- **skills**: Migrated and integrated the purged highlighting and Map-Reduce synthesis prompts into `smart_highlighter` and `note_generator`.

### Architecture (Antigravity Context)
- **OOM Defense & RAM Guard**: Addressed Ollama OOM crashes via explicit model unloading (`keep_alive=0`), Context Window bounds, and a proactive RAM Guard (throttles tasks below 15% available RAM).
- **Non-blocking Task Queue**: Implemented a professional Job Queue for strictly sequential task execution, eliminating asynchronous blocking risks and introducing frontend status polling.
- **Audio-Transcriber Anti-Hallucination**: Consolidated a three-tier defense (Native API tuning, VAD pre-processing, Repetition Detection), integrated multi-clip language detection, and updated to `mx.clear_cache` to resolve deprecation warnings.
- **Strict Sandboxed Routing**: Resolved I/O data leakage ensuring pure single-responsibility isolation. `doc_parser` exclusively handles PDFs, decoupled from processing logic like `note_generator`.
- **Bidirectional Ecosystem Integration**: Finalized local-first, zero-latency workflows synchronizing Open WebUI with the Obsidian Vault.
- **WebUI to CLI Convergence**: Streamlined architecture post WebUI/CLI functional parity, standardizing entirely on headless CLI infrastructure and automated file routing.
- **Omega Integration & Code Self-Healing**: Ported the `audio_transcriber` DAG dashboard, interactive selection UI, and preflight check mechanisms to all other skills (`doc_parser`, `interactive_reader`, `knowledge_compiler`, `academic_edu_assistant`).
- **Global Documentation Consolidation**: Enforced the Anti-Truncation Protocol by executing a full-scale ingestion of `openclaw-sandbox/docs/` into the root `/docs/` repository, designating `/docs/` as the sole Single Source of Truth (SSoT).

---

## [0.9.0] — 2026-04-19

### Added

- `core/inbox_config.json`: 42 configurable PDF routing rules supporting three dispatch modes —
  `audio_ref` (reference-only for audio proofreading), `doc_parser` (full Markdown extraction),
  and `both` (atomic copy to both destinations simultaneously). Rules are hot-reloaded on every
  file event; no daemon restart required.
- `skills/inbox_manager/`: CLI skill exposing `query.py` for runtime inspection and mutation of
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
- `skills/audio_transcriber/scripts/phases/p05_synthesis.py`: final output corrected from
  `data/raw/` to `data/wiki/<subject>/` — eliminates infinite re-ingestion loop.
- `skills/doc_parser/scripts/phases/p03_synthesis.py`: same correction applied.
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

- `memory/` AI collaboration layer in `openclaw-sandbox/`
- `infra/` directory consolidating LiteLLM, Open WebUI, Pipelines, and lifecycle scripts
- `.github/` with CI lint workflow and issue/PR templates
- `tests/` directory structure (e2e + integration stubs)
- `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md` at repo root
- `.editorconfig` and `pyproject.toml` at repo root

### Changed

- `pyproject.toml` and `.pre-commit-config.yaml` moved to `openclaw-sandbox/` root
- `CODING_GUIDELINES.md` v3.0.0 — merged all prior rules documents

### Removed

- `ops/config/` directory (config files promoted to workspace root)
- `ops/migrate_data_layout.py` (one-off migration script, executed and retired)

---

## [0.1.0] — 2026-04-15

### Added

- Initial `openclaw-sandbox/` sandbox structure
- `core/` shared framework (`PipelineBase`, `PathBuilder`, `StateManager`, `LogManager`, etc.)
- `audio_transcriber` skill — 6-phase MLX-Whisper pipeline
- `doc_parser` skill — 7-phase Docling pipeline
- Inbox Daemon for automatic file routing and pipeline triggering


## [v1.2.0] - 2026-04-30 Multi-Agent Architecture Update
- **Added**: Global State & Memory Pool via `MemoryPool` in `state_manager.py`.
- **Added**: Dynamic Routing & Task Decomposition via `RouterAgent` LLM parsing.
- **Added**: HITL Pipeline Resumption with `HITLPendingInterrupt` checkpointing.
- **Added**: Fully Async LLM Generation using `aiohttp` and `tenacity`.
- **Added**: `rich`-based terminal UI formatting.

### Legacy Sandbox Changelog

# Open Claw — Changelog

All notable changes to the Open Claw ecosystem will be documented in this file.

## [2.0.0] - 2026-04-22 ("Antigravity" Checkpoint)

### Architecture
- **Headless Migration**: Deprecated and removed legacy Flask WebUI components in favor of a resilient background daemon architecture.
- **LocalTaskQueue (RAM Guard)**: Introduced a strictly single-threaded global queue (`core/task_queue.py`) with `run_pipelines.lock`. Completely eliminates concurrent Model initialization and OS-level Out-Of-Memory (OOM) crashes.
- **Dead Letter Quarantine (DLQ)**: Implemented advanced failure isolation. Poisonous payloads that exceed `max_retries=3` or cause deterministic faults are intercepted and relocated to `data/quarantine/` with robust telemetry.
- **Data Flow Decoupling**: Extracted high-level synthesis logic out of `audio_transcriber` and `doc_parser` into dedicated synthesis skills (`note-generator`, `smart-highlighter`).

### Core & Observability
- **DRY Modularity**: Unified redundant filesystem operations into `core/file_utils.py` (`safe_read_json`, `managed_tmp_dir`, `ensure_dir`).
- **Structured Telemetry**: Integrated `JsonFormatter` into `core/log_manager.py`. Toggled via `OPENCLAW_LOG_JSON=1`, enabling seamless upstream log aggregation for headless operations.
- **Deterministic Exception Tracking**: Enforced `exc_info=True` across all critical exception handlers in `SystemInboxDaemon` and `StateManager` to eradicate silent fault swallowing.
- **Automated Validation**: Bootstrapped the foundational `pytest` suite within `tests/` to guarantee invariants for core subsystems (`AtomicWriter`, `ResumeManager`, etc.).
- **UI & UX**: `feat(global): standardized notification and UI across all skill modules`.

### Ecosystem Integrations
- **LiteLLM & ChromaDB**: Finalized integrations for semantic RAG routing.
- **Obsidian Bidirectional Sync**: Engineered atomic debouncing (`watchdog`) capable of triggering background refinement pipelines via Obsidian YAML metadata updates (`status: rewrite`).

### Anti-Hallucination & Model Safety
- **Strict Temperature Enforcement**: Hardcoded `temperature: 0` inside `knowledge_compiler` and `interactive_reader` configs to eliminate non-deterministic hallucinations.
- **VLM Pipeline Hardening**: Overhauled `p01d_vlm_vision.py` to dynamically index Markdown tables, handle missing images gracefully, and execute atomic commits.
- **VAD Safety Valve**: Enhanced `p01_transcribe.py` with `pydub.silence`. Introduced a failsafe `max_removal_ratio` trigger to automatically fall back to the raw audio if aggressive VAD thresholds mutilate the context.

## [1.0.0] - Initial Release
- Monolithic Flask-based architecture.
- Basic Audio and Document pipelines.
