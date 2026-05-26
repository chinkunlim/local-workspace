# CHANGELOG.md — Open Claw Sandbox

All notable changes to `openclaw-sandbox/` are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [V9.20] — 2026-05-25: Proofreader Optimization & Auto-Checklist Logging

### Added
- **Automated HITL Trace Logging**: `PipelineBase.process_tasks()` now catches `HITLPendingInterrupt` automatically and stores the exception reason (which contains the trace ID and context) into the `StateManager`'s `note_tag`. Skills no longer need manual state update calls before triggering HITL.
- **Reference Doc Tracking**: `proofreader` now tracks the exact reference document filenames used during validation and saves them to `note_tag` (e.g. `📚 參考: L03_raw_extracted.md`).

### Changed
- **Proofreader Model Unloading**: Optimized `proofreader` LLM handling. It now tracks models loaded during execution (`self._used_models`) and explicitly calls `unload_model()` only at the end of the phase (`run()`) rather than unloading after every individual file. This drastically improves batch processing speed.
- **Inbox Daemon Guidelines**: Clarified `--scan-only` behavior for `inbox_daemon.py` which executes distribution and immediately exits without leaving background monitoring threads running.

---

## [V9.19] — 2026-05-24: VAD Safety Limits & Global Clear Flag

### Added
- **Global `--clear` CLI Flag**: Implemented `--clear` (and `-c`) universally across all 12 pipeline skills. Resolves the pain point of needing to manually delete `state.json` or output folders to restart a skill.
- **`StateManager.clear_progress()`**: New method to safely reset all registered phase records back to `⏳` and purge hashes, notes, and checkpoints without deleting physical output files.
- **Dynamic VAD Ratio Logging**: `audio_transcriber` now injects a dynamic Note Tag (`VAD 移除靜音 XX.X%`) into the pipeline DAG checklist when silence removal is performed.

### Changed
- **VAD Safety Valve**: Configured `vad_max_removal_ratio` in `audio_transcriber` config to `0.10` (10%). `vad_preprocess()` now automatically triggers a safety fallback, bypassing silence removal entirely if the VAD engine strips more than 10% of the audio track (indicates false-positive triggers on background music).
- **Skill Parsers (`core/cli/cli.py`)**: Centralized `build_skill_parser()` now accepts `include_clear=True` to enforce consistent arguments.
- **Pipeline Orchestrators**: Upgraded all Batch A (`Orchestrator` classes) and Batch B (`PipelineBase.run_skill_pipeline()`) entry points to intercept the `--clear` flag, invoke `clear_progress()`, and early-exit cleanly.

---
## [V9.18] — 2026-05-23: OpenClaw Native Pipeline Skills Integration (ADR-013)

### Added
- **Native OpenClaw Agent Integration**: Pipeline skills (`doc_parser`, `audio_transcriber`, etc.) are now natively recognized by the OpenClaw Agent. `SKILL.md` files are hard-copied to `~/.openclaw/skills/` to bypass the `symlink-escape` security restriction.
- **ADR-013**: Documented the architectural decision to unify Telegram bot interfaces and expose Pipeline Skills to the OpenClaw CLI Agent via hard-copied SKILL manifests.

### Deprecated
- **`bot_daemon.py`**: The dedicated pipeline Telegram bot is deprecated in favor of a single-bot architecture using OpenClaw's native Telegram plugin.

---

## [V9.17] — 2026-05-23: Coding Guidelines Full Compliance Audit
### Fixed
- **`gemini_verifier_agent/p01_ai_debate.py`**: Repaired unclosed parenthesis in `super().__init__()` — was causing Ruff parse failure and Mypy type-check cascade errors.
- **14 bare `print()` violations (§8.1)**: Migrated to structured `self.info/self.error/self.warning/self.log` calls:
  - `student_researcher/p01_claim_extraction.py` — 4 calls
  - `student_researcher/p02_synthesis.py` — 6 calls
  - `gemini_verifier_agent/p01_ai_debate.py` — 4 calls

### Changed
- **`knowledge_compiler/p02_extract_graph.py`**: Removed manual `OllamaClient()` instantiation; now reuses `self.llm` from `PipelineBase` (§8.1 `self.llm` Invariant).
- **`doc_parser/p00b_png_pipeline.py`**: Removed manual `OllamaClient(api_url=...)` instantiation; now reuses `self.llm`.

### Documentation
- **ADR-017**: Sequential Shared-SSoT Cognitive Chain — codified as immutable architectural invariant.
- **ADR-018**: Coding Guidelines Full Compliance — structured logging & `PipelineBase.self.llm` invariant.
- **`docs/ARCHITECTURE.md`** (global): Updated `Last Updated`, `CODING_GUIDELINES` version, added V9.17 compliance audit to Historical Evolution.
- **`docs/USER_MANUAL.md`**: Complete rewrite from V9.2 → V9.17. Added HITL Dashboard, Sequential SSoT Chain, student_researcher Multi-Ingress Funnel, Stub Note Mode.
- **`docs/INDEX.md`**: Added `proofreader`, `student_researcher`, `academic_library_agent`, `gemini_verifier_agent` to skill table.
- **`AGENTS.md`**: Expanded from 9 to 13 skills; added Sequential SSoT Chain, HITL, Stub Note Mode descriptions.

### Quality Gate
- Ruff lint: ✅ 0 errors | Ruff format: ✅ | Mypy: ✅ 0 errors (147 files) | pytest: ✅ 22 passed, 5 skipped

---

## [V9.16] — 2026-05-22: student_researcher Multi-Ingress Funnel Architecture

### Added
- **Multi-Ingress Funnel (student_researcher)**: Formally accepts three independent input streams:
  1. Chat/Q&A Markdown files from `data/raw/` (auto-routed to staging, manually triggered)
  2. Telegram `/idea` captures (bypass Layer 2, auto-staged, manually triggered)
  3. `proofreader` verified output from `04_final_verified/` (auto-staged, manually triggered)
- **Strict Manual Trigger Gate**: `student_researcher` is excluded from all automated pipeline chains. Inputs stage in `data/student_researcher/input/`. Execution requires explicit `uv run skills/student_researcher/scripts/run_all.py`.

### Architecture
- **5-Layer Dual-Track finalized**: Ingestion → Extraction → HITL Gate → Sequential SSoT Chain → Compilation.
- **Sequential Shared-SSoT Chain**: `smart_highlighter` ➔ `note_generator` ➔ `feynman_simulator` ➔ `academic_edu_assistant`. Each station independently reads the same `04_final_verified/` — never consuming the prior station's LLM output.

---

## [V9.15] — 2026-05-22: VLM Memory Hardening & HITL Centralization

### Fixed
- **VLM OOM**: `asyncio.Semaphore(1)` enforced for `llama3.2-vision` in `p01d_vlm_vision.py`. Semaphore(2) caused 10-minute API timeout on 16 GB Apple Silicon.
- **HITL Interrupt Propagation**: `HITLPendingInterrupt` now explicitly caught in `p01c_ocr_gate.py`; no longer swallowed by generic `except Exception`.
- **Telegram Notification Centralization**: Moved `send_hitl_prompt` to `HITLManager.trigger()`. Phase scripts no longer construct Telegram messages directly.

### Added
- **ADR-015**: VLM Concurrency Limitation + Centralized HITL Notification.
- **`CODING_GUIDELINES.md` §5.11**: VLM `Semaphore(1)` invariant — heavy vision models (`llama3.2-vision`) must never run concurrently.
- **`CODING_GUIDELINES.md` §5.12**: HITL Interrupt Propagation Invariant — `HITLPendingInterrupt` must never be caught by generic `except Exception`.
- **E2E & Integration Test Stubs**: `tests/e2e/test_pipeline_e2e.py`, `tests/integration/test_vlm_integration.py` (CODING_GUIDELINES §11.2).

---

## [V9.14] — 2026-05-22: HITL Proofreader Pipeline Pause/Resume

### Added
- **Pipeline Pause Mechanism**: `RouterAgent` now detects when the next skill in a chain is `proofreader`. Instead of blindly enqueuing it and blocking a background thread, it pauses the chain execution by writing the remaining sequence to `pending_chains.json` and prints a console/Telegram prompt for human intervention.
- **Watchdog Pipeline Resume**: `inbox_daemon.py` now includes a dedicated watchdog handler that monitors `data/proofreader/output/04_final_verified/`. Upon detecting a newly verified file, it locates the corresponding `pending_chains.json` and emits a `PipelineCompleted` event to seamlessly resume the paused execution string (e.g., triggering `smart_highlighter`).
- **Dashboard Force Skip**: A new `/api/skip` endpoint and a ⏭️ Skip & Forward UI button were added to the `proofreader` Dashboard. This allows users to explicitly bypass the manual modification step, instantly copying the raw AI output directly to the verified directory to resume the pipeline.

### Changed
- **Config-Driven Pre-Chains**: `proofreader` was formally inserted into the `_DEFAULT_CHAINS` for both `audio_transcriber` and `doc_parser` within `RouterAgent`, establishing it as the absolute bottleneck between transcription and annotation (as requested).
- **Skill Path Resolution**: `SkillRunner.resolve_highlight_paths()` and `resolve_synthesize_paths()` were patched to gracefully support `proofreader` as an emitting `current_skill`, accurately mapping cross-skill input folders to `04_final_verified`.

## [V9.13] — 2026-05-22: Semantic Router & Idea Incubator

### Added
- **Phase 0 Semantic Router (`p00_semantic_router.py`)**: Added to `student_researcher` to generate LLM summaries of input ideas and perform ChromaDB semantic vector search to identify related subjects automatically.
- **Idea Incubator Concept**: If `p00_semantic_router.py` finds no highly related knowledge, the file is designated as an orphan. It is assigned to the `Incubator` target subject and generated 3 ontological `#tags`.
- **Knowledge Compiler Extension**: Adjusted architecture so that after Phase 2 Synthesis, `student_researcher` directly hands off the pure summarized idea/notes to `knowledge_compiler` via `RouterAgent`, bypassing the Deep Verification layer (Layer 4) initially.
- **Router Agent Handoff Fix**: Fixed `_on_pipeline_completed` in `router_agent.py` to properly `os.rename` handoff files between `student_researcher` and `knowledge_compiler`.
- **15-Skill Architecture Documentation**: Extensively updated architecture documentation mapping all 15 skills and 6 layers of the system.

### Changed
- **Deep Verification as Extension**: `academic_library_agent` and `gemini_verifier_agent` are now optional, asynchronous extensions that create "Extension Packs" appended to the knowledge base without polluting the original unstructured idea/note.

---

## [V9.12] — 2026-05-22: VLM Stability & HITL Notification Fixes

### Fixed
- **VLM Out-Of-Memory / Timeout**: Reduced `asyncio.Semaphore` limit from 2 to 1 in `p01d_vlm_vision.py` for `llama3.2-vision:latest` to prevent 16GB unified memory environments from thrashing and triggering 10-minute API timeouts (Tenacity Circuit Breaker trips).
- **HITL Interrupt Propagation**: Explicitly caught `HITLPendingInterrupt` in `p01c_ocr_gate.py` to prevent it from being swallowed by the generic `Exception` catch-all. The pipeline now successfully pauses and awaits user intervention via Telegram/Console instead of blindly proceeding.
- **Telegram Notification Centralization**: Moved `send_hitl_prompt` emission into `HITLManager.trigger()` (resolving TODO #14 in `hitl_manager.py`). Phase scripts no longer need to manually construct Telegram messages.

### Added
- **E2E & Integration Test Stubs**: Created `tests/e2e/test_pipeline_e2e.py` and `tests/integration/test_vlm_integration.py` to satisfy `CODING_GUIDELINES §11.2` requirements for downstream testing.

---

## [V9.11] — 2026-05-14: Proofreader DAG State Architecture Fix### Fixed
- **Proofreader DAG Ping-Pong Loop**: Removed legacy `self.state_manager.raw_dir` overrides and manual `os.listdir()` state mutations from `p02_transcript_proofread.py` and `p03_doc_completeness.py`. These scripts previously forced `sync_physical_files()` to scan intermediate output directories, resulting in false-positive hash mismatches and infinite `⏳` resets. Orchestration is now strictly top-down via `run_all.py`.
- **`run_all.py` Hash Initialization**: Updated `_populate_state_from_sources()` to compute the actual `SHA-256` hash of source files (from `01_processed` or `03_merged`) upon initial state insertion instead of defaulting to `""`. This prevents `sync_physical_files()` from invalidating the state on the very first run.

### Changed
- **Proofreader "Source of Truth" Pipeline**: Fully integrated the `dashboard.py` human-in-the-loop workflow. Downstream skills (`note_generator`, `smart_highlighter`) now properly consume from the verified `04_final_verified/` directory, while `02_transcript_proofread/` preserves the raw `<ProofreadChoice>` XML AI output.

### Quality Gate
- Ruff lint: ✅ (see latest check.sh run)
- Mypy: ✅ (no new type errors introduced)

---

### Changed
- **`RouterAgent._build_routing_table()`**: Replaced the hardcoded `_ROUTING_TABLE` global dict with an instance-level `_build_routing_table()` method. Reads `core/config/inbox_config.json` at init time. The `ext:auto` routing table is constructed from `_GROUP_FIRST_SKILL` × `_DEFAULT_CHAINS` × `_EXTRACT_ONLY_EXTS` constants. `_INTENT_ROUTES` (intent-specific overrides like `.pdf:study`) remain in code as they are orchestration logic, not file-type config.
- **`inbox_daemon.py` single-responsibility cleanup**: Removed `_load_config()` method (31 lines), `self.routing_rules` dict, and `self.pdf_routing_rules` list. All routing is now owned exclusively by `RouterAgent._build_routing_table()`.

### Added
- **`Phase0cMarkItDown._extract_pptx_images()`**: Extracts embedded image blobs from PPTX files using python-pptx. Images saved to the same directory as `raw_extracted.md` using MarkItDown's exact filename convention (`re.sub(r"\W", "", shape.name) + ".jpg"`), ensuring all `![...](filename)` references in the generated Markdown resolve without post-processing. Recurses into group shapes.
- **`figure_list.md` real filenames**: Now populated with actual extracted image filenames from PPTX blobs (previously a generic placeholder).

### Docs
- **`skills/doc_parser/docs/ARCHITECTURE.md` → V4.0**: Pipeline DAG diagram updated to show 3-branch routing (Office / PDF / Image). Phases directory listing includes `p00c_markitdown.py`. State tracking phase set updated.
- **`skills/doc_parser/docs/DECISIONS.md`**: Added PPTX image extraction ADR with rationale for co-location vs assets/ subdirectory.

### Quality Gate
- Ruff lint: ✅ (0 errors)
- Mypy: ✅ (0 errors, 144 files)

---

## [V9.10] — 2026-05-13: MarkItDown Integration, RouterAgent Config-Driven Routing & Proofreader DAG Fixes

### Added
- **`doc_parser/p00c_markitdown.py` — Phase 0c**: New `Phase0cMarkItDown` using `markitdown[pptx,docx,xlsx]` (MIT). Converts `.pptx`, `.docx`, `.xlsx` to `{file_id}_raw_extracted.md`. PPTX speaker notes preserved as `### Notes:` blocks. Output interface identical to `Phase1aPDFEngine` — zero downstream changes needed.
- **`RouterAgent._build_routing_table()`**: Reads `core/config/inbox_config.json` at init to build the `ext:auto` routing table dynamically. Intent-specific overrides (`_INTENT_ROUTES`) remain in code. See ADR-013.
- **`inbox_config.json` extended**: `.pptx`, `.docx`, `.xlsx` added to `pdf_knowledge` routing group.
- **`state_manager.py` — Phase `p0c`**: `PHASES_PDF` now includes `p0c`; `file_ext` extended with Office extensions.

### Fixed
- **Proofreader DAG pollution (`correction_log.md`)**: Proofreader phases (`p02`, `p03`) and `run_all.py` Manual State Injection loops now filter `correction_log.md` explicitly. `state_manager.py` `sync_physical_files` also skips it. Fixes inflating P1/P2 DAG counts and P2 state resetting across multiple pipeline runs.
- **`doc_parser/run_all.py` — 3-branch DAG masking**: Masking logic now handles PDF (skip `p0c`, `p0b`), Image (skip `p0c` + all text phases), and Office (skip all PDF-specific phases) as separate branches.

### Changed
- **`inbox_daemon.py`**: Removed duplicate `_load_config()` method — routing is now entirely owned by `RouterAgent._build_routing_table()`. Single Responsibility achieved.

### Docs
- **`CODING_GUIDELINES §5.4`**: Added "Log File Filter Invariant" — all state population loops must explicitly skip `correction_log.md`.
- **`memory/DECISIONS.md`**: Added ADR-013 (Config-Driven RouterAgent Routing).
- **`skills/doc_parser/docs/DECISIONS.md`**: Added MarkItDown integration ADR with full rationale.

### Quality Gate
- Ruff lint: ✅ (0 errors)
- Mypy: ✅ (0 errors)

---

## [V9.9] — 2026-05-13: Doc-Parser & Proofreader Pipeline Standardization

### Fixed
- **`doc_parser/p01c_ocr_gate.py`**: Corrected `phase_key` from `"phase1c"` → `"p1c"` to match `StateManager` canonical keys, preventing completed P1c tasks from being re-queued.
- **`doc_parser/p01d_vlm_vision.py`**: Corrected `phase_key` from `"phase1d"` → `"p1d"`; added missing `pdf_path` variable declaration in `_process_file` (was raising `NameError` during EventBus handoff).
- **`core/state/global_registry.py`**: Changed `threading.Lock()` → `threading.RLock()` to eliminate deadlock when `get_asset_paths()` calls `get_assets()` within the same thread.
- **`proofreader/p01_doc_proofread.py`**: Enforced `p2`/`p3` mask re-application on existing state entries (prevents `sync_physical_files` overwrites from stripping `⏭️` masks).
- **`proofreader/p02_transcript_proofread.py`**: Replaced `sync_physical_files()` call with Manual State Injection — preserves existing state, enforces `p1: ⏭️` mask for audio-sourced files.
- **`proofreader/p03_doc_completeness.py`**: Replaced `sync_physical_files()` call with Manual State Injection — preserves existing state, enforces `p1: ⏭️` mask.
- **`proofreader/run_all.py`**: Enforced continuous mask re-application in `_populate_state_from_sources()` for both doc-source (`p2`/`p3`: `⏭️`) and audio-source (`p1`: `⏭️`) entries.
- **`core/orchestration/router_agent.py`**: Fixed proofreader wakeup cmd — was calling non-existent `scripts/phases/p01_transcript_proofread.py`; corrected to `scripts/run_all.py`.
- **`infra/scripts/start.sh`**: Fixed `inbox_daemon` path (`core/inbox_daemon.py` → `core/services/inbox_daemon.py`).
- **`infra/scripts/stop.sh`**: Fixed `pkill` fallback path for `inbox_daemon` to match corrected location.

### Added
- **`infra/scripts/start.sh` — Proofreader Dashboard**: Added Step 8 to launch `skills/proofreader/scripts/dashboard.py` on port `8081` at startup; auto-opens browser; listed in SERVICE DASHBOARD summary.
- **`infra/scripts/stop.sh`**: Added `kill_by_port 8081` and `check_status 8081` for Proofreader UI cleanup.
- **`infra/scripts/Start OpenClaw Bot.app`**: macOS Automator Applet wrapping `start_bot.sh` for one-click Telegram Bot launch.

### Changed
- **`docs/CODING_GUIDELINES.md` §5.4**: Added new invariant documenting `sync_physical_files()` vs Manual State Injection contract for single-source vs multi-source converging pipelines.

### Quality Gate
- Ruff lint: ✅ (see latest `check.sh` run)
- Mypy: ✅ (no new type errors introduced)

---

## [V9.8] — 2026-05-12: uv-Native Toolchain Migration & Quality Gate Hardening

### Changed
- **Dependency management migrated to `uv`**: `requirements.txt` and `requirements.in` removed. All 160+ runtime and dev dependencies now live exclusively in `pyproject.toml` + `uv.lock`. `[project]` table added to enable `uv add`.
- **`ops/check.sh` uv-hardened**: Replaced bare `ruff check`, `ruff format`, `mypy` calls with `uv run ruff` / `uv run mypy`. Eliminates `command not found` failures on clean environments where tools are only available via the project `.venv`.

### Fixed
- **`academic_library_agent/p01_search_literature.py`**: Repaired broken `_save_evidence()` method (dangling indented line, reference to undefined `results`/`out_path`). Added missing `run()` orchestration entry point.
- **`gemini_verifier_agent/p01_ai_debate.py`**: Fixed missing `except` clause after `try` block (syntax error blocking Ruff format & Mypy). Corrected `_debate_gemini` return type annotation to `str | None`.
- **`core/state/global_registry.py`**: Fixed 4 Mypy type errors — `_memory_cache` type annotation changed from implicit `None` to `Optional[Dict]`; added `# type: ignore[return-value]` on guarded return path.

### Added
- **`litellm==1.83.0`** and **`python-telegram-bot==22.7`**: Were missing from `pyproject.toml` despite being imported by core services. Added via `uv add`.
- **Whisper models downloaded**: `mlx-community/whisper-large-v3-mlx` (HF Hub) and `Systran/faster-whisper-medium` fully downloaded to `models/` (4.3 GB total) with `HF_HOME` sandboxed inside project.

### Quality Gate
- Ruff lint: ✅ 0 errors (162 files)
- Ruff format: ✅ 162 files clean
- Mypy: ✅ 0 errors in 143 source files
- pytest: ✅ 18 passed, 5 skipped (0 failures)

---

## [V9.6] — 2026-05-08: Synthesis Pipeline CLI Standardisation & DAG Hardening

### Added
- **`SmartHighlighterOrchestrator`** (`smart_highlighter/scripts/run_all.py` [NEW]): Full pipeline runner with `StateManager` DAG tracking, dual file/batch mode, `--force/--resume/--subject/--file` CLI, and automatic `assets/` directory copying for image path resolution.
- **`NoteGeneratorOrchestrator`** (`note_generator/scripts/run_all.py` [NEW]): Identical architecture as above. Adds `strip_think_tags()` (removes `<think>...</think>` reasoning blocks from models like `phi4-mini-reasoning`) and `fix_mermaid_syntax()` (auto-repairs broken `mindmap` declarations).
- **`StateManager.raw_dir` override parameter**: Skills with cross-skill input paths can now explicitly provide their scan directory, decoupling the DAG from the default `input/` folder.
- **`StateManager` Phase Registration**: `PHASES_HIGHLIGHT = ["highlight"]` / `PHASES_NOTE = ["synthesize"]` with labels `H1 (重點標記)` / `N1 (知識合成)` displayed in the DAG dashboard.
- **`CODING_GUIDELINES.md` §5.5–5.8**: Four new invariants: `skill_name` underscore convention, `run_all.py` entry point naming, reasoning model `<think>` stripping, and `StateManager raw_dir` override.

### Fixed
- **`audio_transcriber/run_all.py` stale import**: `Phase2Proofread` → `Phase2GlossaryApply` (previous refactor left a dead import causing `ModuleNotFoundError`).
- **`smart_highlighter/scripts/highlight.py` `skill_name` bug**: Changed `"smart-highlighter"` (hyphen) to `"smart_highlighter"` (underscore). `PathBuilder` was silently unable to resolve `config.yaml`.

### Changed
- **`note_generator/config.yaml` timeout**: Increased `runtime.ollama.timeout_seconds` from 600 → 1800 to support long 8-model synthesis outputs.
- **Both `manifest.py`**: `cli_entry` updated from `synthesize.py`/`highlight.py` → `scripts/run_all.py`.

---

## [V9.5] — 2026-05-07: Advanced Prompt Engineering & Routing Architecture

### Added
- **Comprehensive Study Guide Model** (`note_generator`): Introduced an 8th model in the synthesis prompt producing an Obsidian-ready deep-dive guide. Includes bilingual headers, GitHub-style alerts, and dynamic Mermaid mind maps.
- **Auto-Hashtag Mechanism**: Enforced a strict rule in `note_generator` to embed italicized `#tags` exactly one line below all `H2`/`H3` headings for precise Dataview block retrieval.
- **Parallel Extraction Architecture** (ADR-011): Formally defined that `smart_highlighter` and `note_generator` run in parallel from `proofreader`'s clean output, eliminating markdown pollution between the annotation and synthesis streams.

### Changed
- **Unified Synthesis Prompt**: Removed legacy "Phase 5" terminology from `synthesize.py`, migrating to a universal `Note Synthesis Instruction` architecture.
- **Smart Highlighter Syntax Expansion**: Expanded allowed annotation syntax to include `**bold**`, `==highlight==`, `*italic*`, `~~strikethrough~~`, `` `inline code` ``, `> blockquote`, and `<u>underline</u>`. Added strict rule preventing deletion of existing `![image]` tags.
- **QEC Model Refinement**: Constrained the 'Evidence' extraction to only the 1-2 most pivotal experiments, shifting exhaustive data lists to dedicated Markdown tables in the Study Guide.

---

## [V9.4] — 2026-05-07: Multi-Format Parse & Asynchronous Verification Pipeline

### Added
- **Asynchronous Verification Dashboard** (`dashboard.py`): A centralized, non-blocking Flask web UI for Human-in-the-Loop verification. It serves `data/proofreader/output/` files and embeds original PDF/PNG/M4A Ground Truth media inline.
- **Phase 0: Doc Proofread** (`p00_doc_proofread.py`): A dedicated proofreading phase for the `doc_parser` pipeline that automatically corrects OCR errors and embeds Markdown images exactly where they logically belong.
- **`pipeline_architecture.md`** (`memory/`): Created an architectural overview of the `doc_parser` ➡️ `proofreader` ⬅️ `audio_transcriber` hand-off mechanisms.

### Changed
- **Deprecated Blocking Verification Gate** (`human_gate.py`): Removed the synchronous `_GatedHTTPServer` from `p00`, `p01`, and `p02` to allow true autonomous background batch processing.
- **Unicode Support in UI**: Fixed the Dashboard's JS `btoa` encoding logic to safely support Unicode file and subject names (e.g., `助人歷程`).

### Fixed
- **Docling Core Recovery**: Repaired the previously corrupted `docling` runtime by enforcing `docling-slim` and resolving absolute module pathing (`sys.path` injection) in `p01a_engine.py`.
- **Mixed-Format Parsers (PDF/PNG)**: Hardened `run_all.py` to seamlessly orchestrate both Tesseract PNG extractions and Docling PDF extractions within the same Subject batch.

---

## [V9.3] — 2026-05-05: Full Mypy Compliance + AI-Native Doc System

### Fixed
- **Global Mypy compliance** (`core/` + `skills/`): Resolved all 41 type errors across 133 source files.
  - `core/ai/llm_client.py`: `aiohttp.ClientTimeout(total=float(...))` wrapping
  - `core/state/state_manager.py`: Added `is_completed()` / `mark_completed()` convenience methods
  - `core/utils/file_utils.py`: Widened `write_csv_safe()` logger param to `object` for duck-typed callers
  - `skills/doc_parser/` (`p01b`, `p01c`, `p01d`): None-guards for threshold/dpi; unload_model str-cast; dict type fixes
  - `skills/knowledge_compiler/p01_compile.py`: ChromaDB query result None-guard
  - `skills/note_generator/synthesize.py`: Fixed `_agentic_mermaid_retry` return type annotation
  - `skills/doc_parser/run_all.py`: Declared `self.interactive: bool = False`
  - `skills/feynman_simulator/`: Fixed method calls to use `is_completed()` / `mark_completed()`
  - 6 skills: Fixed `PhaseBase` import path (`core.orchestration.pipeline_base`)

### Changed
- **`ops/check.sh`**: Mypy scope expanded from `core/` → `core/ + skills/` (133 files). Type regressions now caught at commit time.
- **`pyproject.toml`**: `python_version` corrected `3.9` → `3.11` to match actual runtime.

### Added
- **`memory/STARTUP.md`** (`local-workspace/memory/`): Canonical 5-Phase startup prompt and full end-of-session close flow. Single reference for all future AI sessions.

---

## [V9.2] — 2026-05-04: Quality-First Model Optimization

### Changed
- **Quality-First Model Routing** (`core/orchestration/router_agent.py`): High-complexity routing model upgraded from `deepseek-r1:14b` → `qwen3:14b` (already installed, stronger multilingual reasoning for Chinese academic tasks).
- **`note_generator`**: Active profile switched from `phi4_reasoning` → `qwen3_reasoning` (`qwen3:14b`). Profile `phi4_reasoning` retained as fallback.
- **`student_researcher`**: Model upgraded from `qwen3:8b` → `deepseek-r1:8b` (CoT reasoning critical for academic claim extraction).
- **`knowledge_compiler`**: Model upgraded from `qwen3:8b` → `qwen3:14b` (improved entity/WikiLink extraction accuracy). Includes `rerank_model`.
- **`gemini_verifier_agent`**: Model upgraded from `qwen3:8b` → `qwen3:14b` (stronger argumentation for AI-to-AI debate with Gemini).
- **`academic_edu_assistant`**: Model upgraded from `qwen3:8b` → `qwen3:14b` (deeper concept comparison for Anki generation).
- **`academic_library_agent`**: Model upgraded from `qwen3:8b` → `qwen3:14b` (more accurate academic paper analysis).
- **`interactive_reader`**: Model upgraded from `qwen3:8b` → `qwen3:14b` (better Q&A quality).
- **`video_ingester`**: Model upgraded from `qwen3:8b` → `qwen3:14b` (richer keyframe descriptions).
- **`telegram_kb_agent`**: RAG model upgraded from `gemma4:e2b` → `gemma4:e4b` (higher-quality RAG answers); `e2b` retained as commented fallback.

### Removed (Ollama)
- `deepseek-r1:14b` (9.0 GB) — replaced by `qwen3:14b` for high-complexity routing.
- `qwen2.5-coder:7b` (4.7 GB) — fully superseded by `qwen3:8b`.
- `llama3.1` (4.9 GB) — no references in any skill config.

### Added
- **`docs/MODEL_SELECTION.md`** (`openclaw-sandbox/docs/`): Complete per-skill model registry documenting primary models, fallback models, rationale, and quick-switch instructions for every skill.

---

## [V9.1] — 2026-05-04: Performance & Robustness Hardening (Phase A)

### Added
- **Semantic Caching** (`core/ai/llm_client.py`): `SqliteSemanticCache` class caches all deterministic (`temperature=0`) LLM responses by `SHA-256(model::prompt)` key in `data/llm_cache.sqlite3`. Zero-dependency, persistent across reboots.
- **Context-Aware Model Routing** (`core/orchestration/router_agent.py`): `RouterAgent.resolve()` now assigns models based on intent complexity. High-complexity intents (`debate`, `research`, `feynman`, `analyze`, `deep`, `study`) use `qwen3:14b`; low-complexity intents use `qwen3:8b`.
- **Exponential Backoff in TaskQueue** (`core/orchestration/task_queue.py`): Failed tasks now wait `5 * 2^retry_count` seconds before being re-enqueued, preventing thundering-herd retry storms. Task-specific `env` kwarg passes environment overrides to subprocesses.
- **Scheduler Queue Safety** (`core/services/scheduler.py`): APScheduler jobs (daily SM-2 push) now dispatch through the `LocalTaskQueue` via `trigger_anki_push()` instead of running synchronously, eliminating concurrent OOM risk with `inbox_daemon`.

---

## [V9.0] — 2026-05-04: Multi-Agent & GraphRAG Upgrades

### Added
- **`feynman_simulator`**: Multi-agent Socratic debate loop using Playwright to bypass login walls. Student Ollama debates Tutor Gemini.
- **GraphRAG Upgrade**: `knowledge_compiler` now extracts implicit relation triples via LLM and persists to local `networkx` (`.gpickle`).
- **Cross-Semester Linking**: `knowledge_compiler` performs ChromaDB Cosine Similarity Search to automatically inject related past notes.
- **Hybrid Retrieval**: `hybrid_retriever.py` gracefully combines 1-hop Graph expansion with dense Vector search.
- **Spaced Repetition Engine**: Pure Python SM-2 algorithm implementation in `core/services/sm2.py` coupled with `scheduler.py` (APScheduler).
- **Telegram Interactive Review**: Users receive daily pushed flashcards and can reply `/reveal <id>` and `/rate <id> <0-5>` directly in Telegram.
- **`video_ingester`**: Multimodal video ingestion pipeline using FFmpeg keyframes and MLX-Whisper word-level transcripts.

## [V8.2] — 2026-05-02: Intent-Driven RouterAgent & EventBus Handoff

### Added
- **`EventBus` Subprocess Bridging**: `TaskQueue` now emits a `PipelineCompleted` event natively when an isolated subprocess completes successfully (`returncode == 0`), solving IPC memory isolation issues.
- **Dynamic Handoff Execution**: `RouterAgent` now subscribes to `PipelineCompleted`, pops the finished skill from the resolved skill chain, determines input/output paths via `SkillRunner.resolve_synthesize_paths()`, and automatically enqueues the next skill.
- **Skill Manifests**: Every skill now exposes a `manifest.py` containing its `cli_entry`, `file_types`, and phases, enabling pure dynamic discovery by `SkillRegistry`.

### Changed
- **`inbox_daemon.py`**: Completely stripped of all hardcoded extension routing rules (e.g. `.m4a`/`.pdf`). All incoming files are now delegated to `RouterAgent` for intent parsing and dynamic skill chain resolution.
- **Documentation**: Comprehensive SSoT update across `USER_MANUAL.md`, `STRUCTURE.md`, `INDEX.md`, `DECISIONS.md`, and `HANDOFF.md` to formally deprecate the legacy static routing architecture and document the new autonomous DAG orchestration.

---

## [2.0.0] — 2026-05-02: GIGO Prevention & Verification Gate Architecture

### Added

#### `core/orchestration/human_gate.py` *(NEW)*
- Universal **Ephemeral WebUI Verification Gate** (`VerificationGate` class).
- Pure standard-library (no Flask/Gradio dependency) — `http.server` only.
- Side-by-side diff: left pane shows raw/verbatim source, right pane shows Ollama-corrected draft (editable `<textarea>`).
- HTML5 audio player with click-to-play seeking: clicking a `[? uncertain | ts ?]` token jumps to that timestamp (−2 s pre-roll).
- "Approve & Resume Pipeline" button submits the final text and shuts the server in-process; pipeline immediately continues.
- Auto port-conflict resolution (scans up to port+100).

#### `audio_transcriber` — Phase 1 (V8.2)
- `word_timestamps=True` enabled for both `mlx-whisper` and `faster-whisper`.
- **Low-Confidence Flagging**: tokens with probability < 60% are wrapped as `[? word | 12.5 ?]` (word + timestamp in seconds).
- **Light Diarization**: gaps > 1.5 s between segments produce a paragraph break (`\n\n`) for natural speaker separation.

#### `audio_transcriber` — Phase 2 Prompt (V7.3)
- **Step 1 — Disfluency Purge**: LLM instructed to remove `uh`, `um`, false starts, and mid-sentence restarts while preserving semantic content.
- **Step 2 — Low-Confidence Flag Resolution**: LLM resolves `[? word | ts ?]` tokens using PDF context and glossary; unresolvable flags are left for human review.

#### `audio_transcriber` — Phase 2 Code
- Integrated `VerificationGate` after full LLM proofreading pass.
- Raw `p1` verbatim transcript shown on left; Ollama-corrected draft on right.
- Audio file served via `/audio` endpoint for click-to-play.

#### `doc_parser` — Phase 1a (V2.0)
- **PyMuPDF 300 DPI Image Extraction**: replaces `PictureItem.get_image()` (low-res) with `fitz.Matrix(300/72)` bbox crop. Graceful fallback if PyMuPDF not installed.
- **Caption Heuristics**: scans up to 5 items below each `PictureItem` for `Fig.`/`Figure`/`圖`/`表` patterns; detected captions written to `figure_list.md`.
- **Anti-Bleed Post-processing**: strips standalone axis-label tokens (< 6 chars, purely numeric/symbol) that chart OCR bleeds into body text.
- `figure_list.md` schema extended: `原始 Caption` column added; `VLM 描述` pre-filled as `已略過 (Caption 存在)` when caption found.

#### `doc_parser` — Phase 1b-S: Text Sanitizer *(NEW)*
- **Strict Phase Isolation**: `raw_extracted.md` is IMMUTABLE. This phase writes `sanitized.md`.
- **Header/Footer Purge**: lines appearing on ≥ 40% of pages (or matching `Page N of M` pattern) are removed.
- **Hyphenation Repair**: merges end-of-line hyphens (`ex-\ntraction` → `extraction`).
- `sanitized.md` carries a provenance metadata header (lines removed, hyphenations fixed).

#### `doc_parser` — Phase 1d VLM
- **Caption Bypass**: figures with pre-existing native captions skip VLM inference entirely (saves VRAM and prevents hallucinated descriptions).

#### `knowledge_compiler` — Phase 1
- **WikiLink Dead-Link Guard**: before writing to vault, scans all `[[Link]]` occurrences and downgrades to plain text any link whose target `.md` does not exist in `wiki_dir`. Prevents Obsidian from accumulating broken link noise.

#### `academic_edu_assistant` — Phase 2 Anki
- Integrated `VerificationGate` before Anki CSV write and AnkiConnect push.
- User reviews generated Q/A cards against source comparison report; edits are persisted to CSV and pushed to Anki only after approval.

---

### Changed

- `doc_parser/run_all.py`: Phase 1b-S (Text Sanitizer) inserted between Phase 1a and Phase 1b-Vector in the pipeline sequence.
- `audio_transcriber/config/prompt.md`: Phase 2 prompt expanded with two-step Disfluency Purge + Flag Resolution instructions.

---

### Design Invariants Enforced

| Invariant                | Enforcement                                                                                                                              |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Immutable Extraction** | Phase 1 (Whisper / Docling) output is verbatim and never modified in-place. All mutations happen in subsequent, explicitly named phases. |
| **Traceable Provenance** | Each phase writes to a distinct file (`raw_extracted.md` → `sanitized.md`) so failures can be isolated to the exact phase.               |
| **Ollama-First HITL**    | `VerificationGate` only opens after Ollama has already done a first-pass correction. The human confirms rather than transcribes.         |
| **No VLM Waste**         | VLM inference is skipped when native metadata (caption) is already available.                                                            |

---

## [1.x.x] — 2026-04 (Pre-GIGO-Prevention Era)

- See `memory/ARCHITECTURE.md` → *Historical Architectural Evolution* for prior milestone descriptions.
