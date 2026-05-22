# TASKS.md — Task Tracker

> **Last Updated:** 2026-05-13 (V9.11 — RouterAgent Config-Driven Routing Refactor + PPTX Image Extraction)

---

## 🔴 High Priority (阻斷性問題 / 核心功能)

*(None currently)*

---

## 1. 優先處理 (High Priority)
- [ ] **Verify Complete End-to-End Incubator Flow**: Drop a raw `.md` file with a `Gemini_` prefix into `data/raw/inbox/`. Verify that `inbox_daemon` routes it to `student_researcher` (Phase 0 -> Phase 1 -> Phase 2), assigns it to `Incubator` or an existing subject, moves it to `knowledge_compiler` via `RouterAgent`, and outputs it into the `wiki/Incubator/` folder in Obsidian.
- [ ] **E2E Stability Test**: Run `.m4a` + `.pdf` + `.pptx` through the full pipeline (`audio_transcriber` → `doc_parser` → `proofreader` → `note_generator`) to ensure pipeline state remains clean and files do not get stuck in intermediate stages.
- [ ] Phase B (Memory & Graph RAG): ChromaDB + NetworkX deep integration
- [x] **Fix stale `openclaw.json` workspace path**: Update `agents.defaults.workspace` from `/Users/limchinkun/Desktop/local-workspace/open-claw-sandbox` → `openclaw-sandbox/` (run `openclaw configure` or `openclaw config set agents.defaults.workspace /Users/limchinkun/Desktop/local-workspace/openclaw-sandbox`)
- [x] **Migrate core/services & core/cli from rich.print to log_manager for stricter compliance**
- [x] **Resolve TODO (P3) #14: emit to telegram_bot in hitl_manager.py**

---

## 🟡 Medium Priority (優化 / 非緊急功能)

- [x] **Test PPTX/DOCX/XLSX pipeline** (V9.10): `.pptx` processed — E2E verified. 5 images extracted, markdown references resolved correctly. ✅

- [ ] **Run live E2E test** (V9.10): Place `.m4a` + `.pdf` + `.pptx` — confirm DAG counts are stable (no correction_log pollution) across multiple runs.
- [x] **Fix `openclaw.json` stale workspace path**: `agents.defaults.workspace` → `openclaw-sandbox` via `openclaw configure`.
- [ ] Run full batch synthesis: `uv run skills/note_generator/scripts/run_all.py --subject 助人技巧 --force`
- [x] Populate `tests/` with E2E and integration test stubs per CODING_GUIDELINES §11.2
- [ ] Rebuild ChromaDB index and validate a Telegram RAG query with `gemma4:e4b`
- [ ] Phase B (Memory & Graph RAG): ChromaDB + NetworkX deep integration
- [x] **Fix stale `openclaw.json` workspace path**: Update `agents.defaults.workspace` from `/Users/limchinkun/Desktop/local-workspace/open-claw-sandbox` → `openclaw-sandbox/` (run `openclaw configure` or `openclaw config set agents.defaults.workspace /Users/limchinkun/Desktop/local-workspace/openclaw-sandbox`)
- [x] **Migrate core/services & core/cli from rich.print to log_manager for stricter compliance**
- [x] **Resolve TODO (P3) #14: emit to telegram_bot in hitl_manager.py**


---

## 🟢 Low Priority (技術債 / 探索性研究)

- [ ] Register any future OCR service in `BOOTSTRAP.md` if/when needed
- [ ] Evaluate `CONTRIBUTING.md` guidelines if workspace becomes multi-contributor

---

## ✅ Completed

- [x] 2026-05-23: **V9.17 Coding Guidelines Full Compliance Audit**
  - Fixed syntax error (unclosed parenthesis in `super().__init__`) in `gemini_verifier_agent/p01_ai_debate.py`.
  - Removed redundant manual `OllamaClient()` instantiation in `knowledge_compiler/p02_extract_graph.py` and `doc_parser/p00b_png_pipeline.py`; both now reuse `self.llm` from `PipelineBase`.
  - Migrated 14 bare `print()` calls in production code to `self.info/self.error/self.warning/self.log` (§8.1 compliance):
    - `student_researcher/p01_claim_extraction.py` (4), `student_researcher/p02_synthesis.py` (6), `gemini_verifier_agent/p01_ai_debate.py` (4).
  - Quality gate: ✅ Ruff lint, ✅ Ruff format, ✅ Mypy 0 errors (147 files), ✅ 22 tests passed.

- [x] 2026-05-22: **V9.14 HITL Proofreader Pipeline Pause/Resume**
  - Integrated `proofreader` into `audio_transcriber` and `doc_parser` default chains.
  - Implemented `RouterAgent` pause logic via `pending_chains.json`.
  - Upgraded `inbox_daemon.py` with Watchdog on `04_final_verified` to resume chains.
  - Added Dashboard Force Skip endpoint and UI button.
  - Updated `cli_runner.py` to resolve `proofreader` input/output paths.

- [x] 2026-05-13: **V9.11 RouterAgent Config-Driven Routing Refactor + PPTX Image Extraction**
  - Replaced hardcoded `_ROUTING_TABLE` global with `_build_routing_table()` reading `inbox_config.json` at init.
  - Added `_GROUP_FIRST_SKILL`, `_DEFAULT_CHAINS`, `_EXTRACT_ONLY_EXTS`, `_INTENT_ROUTES` constants.
  - Removed dead `_load_config()` / `self.routing_rules` / `self.pdf_routing_rules` from `inbox_daemon.py`.
  - Added `_extract_pptx_images()` to `Phase0cMarkItDown` using python-pptx; 5 images extracted from test PPTX.
  - PPTX image filename convention matches MarkItDown exactly — markdown refs work without path changes.
  - `figure_list.md` now lists real extracted filenames.
  - `doc_parser/docs/ARCHITECTURE.md` updated to V4.0 with 3-branch DAG diagram.
  - `doc_parser/docs/DECISIONS.md` updated with PPTX image extraction ADR.

- [x] 2026-05-13: V9.10 MarkItDown Integration, RouterAgent Config-Driven Routing & Proofreader DAG Fixes
  - Fixed `correction_log.md` DAG pollution: added filter in Manual State Injection loops in `p02`, `p03`, `proofreader/run_all.py`, and `state_manager.py`.
  - Added `Phase0cMarkItDown` (`p00c_markitdown.py`) — PPTX/DOCX/XLSX → Markdown conversion via `markitdown`.
  - Updated `doc_parser/run_all.py` with 3-branch DAG masking (PDF / Image / Office).
  - Extended `state_manager.py`: `PHASES_PDF` += `p0c`; `file_ext` += Office extensions.
  - Refactored `RouterAgent` with `_build_routing_table()` — reads `inbox_config.json` dynamically.
  - Removed duplicate `_load_config()` from `inbox_daemon.py` (routing fully in RouterAgent).
  - Added `.pptx`, `.docx`, `.xlsx` to `inbox_config.json` `pdf_knowledge` group.
  - Added "Log File Filter Invariant" to `CODING_GUIDELINES §5.4`.
  - Documented ADR-013 (config-driven routing) in `memory/DECISIONS.md`.
  - Documented MarkItDown ADR in `skills/doc_parser/docs/DECISIONS.md`.

  - Fixed `phase_key` mismatch in `p01c_ocr_gate.py` (`phase1c` → `p1c`) and `p01d_vlm_vision.py` (`phase1d` → `p1d`).
  - Fixed `NameError` in `p01d_vlm_vision.py` — missing `pdf_path` declaration before EventBus callback.
  - Fixed `GlobalRegistry` deadlock: `threading.Lock()` → `threading.RLock()`.
  - Replaced `sync_physical_files()` in `p02_transcript_proofread.py` and `p03_doc_completeness.py` with Manual State Injection.
  - Enforced continuous `⏭️` mask re-application in all proofreader phases and `run_all.py`.
  - Fixed `RouterAgent` proofreader wakeup to call `scripts/run_all.py` (not individual phase script).
  - Added Proofreader Dashboard (port `8081`) to `start.sh` and `stop.sh`.
  - Fixed `inbox_daemon` path in `start.sh`/`stop.sh`: `core/inbox_daemon.py` → `core/services/inbox_daemon.py`.
  - Documented `sync_physical_files()` vs Manual State Injection in `CODING_GUIDELINES §5.4`.

- [x] 2026-05-12: V9.8 uv-Native Toolchain Migration & Quality Gate Hardening
  - `requirements.txt` and `requirements.in` removed; all 160+ deps migrated to `pyproject.toml` + `uv.lock`.
  - Added `[project]` table to `pyproject.toml` to enable `uv add`.
  - `ruff`, `mypy`, `pytest` added as dev dependencies via `uv add --dev`.
  - `openclaw-sandbox/ops/check.sh` updated: bare `ruff`/`mypy` calls replaced with `uv run ruff`/`uv run mypy`.
  - Fixed syntax errors in `academic_library_agent/p01_search_literature.py` and `gemini_verifier_agent/p01_ai_debate.py`.
  - Fixed 4 Mypy type errors in `core/state/global_registry.py`.
  - Added missing `litellm` and `python-telegram-bot` via `uv add`.
  - MLX-Whisper (`mlx-community/whisper-large-v3-mlx`) and Faster-Whisper (`medium`) models downloaded to `models/`.
  - `check.sh`: ✅ Ruff lint, ✅ Ruff format, ✅ Mypy 0 errors in 143 files.
  - Tests: 18 passed, 5 skipped — 0 failures.
  - GitHub push authenticated via PAT + `gh auth setup-git`.

- [x] 2026-05-10: V9.7 Proofreader & Global Registry
  - `audio_transcriber` `run_all.py` stale import fixed (`Phase2Proofread` → `Phase2GlossaryApply`).
  - `smart_highlighter` → `run_all.py` with `SmartHighlighterOrchestrator`, DAG `H1 (重點標記)`, asset copying.
  - `note_generator` → `run_all.py` with `NoteGeneratorOrchestrator`, DAG `N1 (知識合成)`, `strip_think_tags()`, `fix_mermaid_syntax()`.
  - `StateManager`: added `raw_dir` override param; registered `PHASES_HIGHLIGHT` and `PHASES_NOTE`.
  - `highlight.py` `skill_name` bug fixed (hyphen → underscore).
  - `note_generator` API timeout increased to 1800s.
  - `CODING_GUIDELINES.md` §5.5–5.8: 4 new OpenClaw invariants documented.

- [x] 2026-05-07: Advanced Prompt Engineering & Routing Architecture (V9.5)
  - `note_generator` upgraded to 8-model format including Obsidian-ready Comprehensive Study Guide and dynamic Mermaid diagrams.
  - `smart_highlighter` expanded to 7 Markdown annotation types, strictly preserving image tags.
  - Defined ADR-011: Dual-Brain Parallelism, ensuring pure extraction logic separation from synthesis logic.
  - Purged legacy "Phase 5" terminology from `note_generator` core scripts.

- [x] 2026-05-07: Multi-Format Parse & Asynchronous Verification Pipeline (V9.4)
  - `docling` core environment recovered (forced `docling-slim` and resolved module pathing in `p01a_engine.py`).
  - Validated end-to-end `doc_parser` functionality for mixed `.png` and `.pdf` input batches.
  - Replaced the blocking `VerificationGate` (`_GatedHTTPServer`) with an asynchronous `dashboard.py`.
  - Rebuilt the verification UI to embed raw Ground Truth media (PDF, PNG, M4A) inline with the Markdown editor.
  - Implemented `p00_doc_proofread` (Phase 0) for direct `.md` proofreading and image-embedding logic.
  - Fixed JS `btoa` Unicode bug for robust file routing in the dashboard.

- [x] 2026-05-05: Full Mypy Compliance + AI-Native Documentation System Hardened
  - Fixed all 41 Mypy type errors across `skills/` (0 errors in 133 files)
  - `ops/check.sh` expanded: Mypy now covers `core/ + skills/`
  - `pyproject.toml`: `python_version` corrected `3.9` → `3.11`
  - `memory/STARTUP.md` [NEW]: Canonical 5-Phase startup prompt + full process docs
  - `identity/AI_PROFILE.md`: Added Principle Acknowledgement rule
  - `memory/PROJECT_RULES.md`: Added §6 Code Review Checklist (10 items); fixed archive timing order



---

## 🔴 High Priority (阻斷性問題 / 核心功能)

*(None currently)*

---

## 🟡 Medium Priority (優化 / 非緊急功能)

- [ ] Populate `tests/` with E2E and integration test stubs per CODING_GUIDELINES §11.2
- [ ] Run live end-to-end pipeline test with new `qwen3:14b` routing: `.m4a` / `.mp4` → `data/wiki/`
- [ ] Rebuild ChromaDB index and validate a Telegram RAG query with `gemma4:e4b`
- [ ] Phase B (Memory & Graph RAG): ChromaDB + NetworkX deep integration

---

## 🟢 Low Priority (技術債 / 探索性研究)

- [ ] Register any future OCR service in `BOOTSTRAP.md` if/when needed
- [ ] Evaluate `CONTRIBUTING.md` guidelines if workspace becomes multi-contributor

---

## ✅ Completed

- [x] 2026-05-07: Multi-Format Parse & Asynchronous Verification Pipeline
  - `docling` core environment recovered (forced `docling-slim` and resolved module pathing in `p01a_engine.py`).
  - Validated end-to-end `doc_parser` functionality for mixed `.png` and `.pdf` input batches.
  - Replaced the blocking `VerificationGate` (`_GatedHTTPServer`) with an asynchronous `dashboard.py`.
  - Rebuilt the verification UI to embed raw Ground Truth media (PDF, PNG, M4A) inline with the Markdown editor.
  - Implemented `p00_doc_proofread` (Phase 0) for direct `.md` proofreading and image-embedding logic.
  - Fixed JS `btoa` Unicode bug for robust file routing in the dashboard.

- [x] 2026-05-05: Audio Pipeline Pathing & Tech Stack Docs
  - Fixed `WORKSPACE_DIR` resolution in `bootstrap.py`, `pipeline_base.py`, and `atomic_writer.py`
  - Fixed `ZeroDivisionError` in `audio_transcriber` VAD handling.
  - Suppressed internal `tqdm` output for `mlx-whisper` and implemented chunk-level `tqdm` progress bar.
  - Created `OPENCLAW_TECH_STACK.md` mapping out security defenses, architectural patterns, multi-agent integrations, and defensive programming.

- [x] 2026-05-04: Quality-First Model Optimization (V9.2)
  - Upgraded all skills to quality-first models (see `docs/MODEL_SELECTION.md`)
  - `note_generator`: phi4-mini-reasoning → qwen3:14b (profile: qwen3_reasoning)
  - `student_researcher`: qwen3:8b → deepseek-r1:8b (CoT claim extraction)
  - `knowledge_compiler`, `gemini_verifier_agent`, `academic_edu_assistant`, `academic_library_agent`, `interactive_reader`, `video_ingester`: qwen3:8b → qwen3:14b
  - `telegram_kb_agent`: gemma4:e2b → gemma4:e4b
  - RouterAgent high-complexity: deepseek-r1:14b → qwen3:14b
  - Cleaned up 3 unused Ollama models: deepseek-r1:14b, qwen2.5-coder:7b, llama3.1 (−23.6GB)
  - Created `openclaw-sandbox/docs/MODEL_SELECTION.md` per-skill model registry
  - Full SSoT documentation sync across all MD files

- [x] 2026-05-04: Phase A Performance Hardening (V9.1)
  - `SqliteSemanticCache` in `core/ai/llm_client.py` (SHA-256 keyed, `data/llm_cache.sqlite3`)
  - Exponential Backoff (`5 * 2^retry_count`) in `task_queue.py`
  - Scheduler Queue Safety: APScheduler jobs → LocalTaskQueue
  - Context-Aware Model Routing in `RouterAgent`
  - ADR-007 and ADR-008 documented in `memory/DECISIONS.md`

- [x] 2026-05-04: Open Claw v9.0 Upgrade — Multi-Agent & GraphRAG
  - Implemented `feynman_simulator` and `video_ingester`
  - Integrated `sm2.py` spaced repetition and `scheduler.py` daemon
  - Performed comprehensive SSoT Documentation Sync

- [x] 2026-05-02: Comprehensive Documentation SSoT Sync
  - `USER_MANUAL.md` updated with Intent-Driven architecture and HITL guide
  - `STRUCTURE.md` and `INDEX.md` updated with `RouterAgent`, `EventBus`, and `TaskQueue` documentation
  - `DECISIONS.md`, `TASKS.md`, and `HANDOFF.md` updated

- [x] 2026-05-01: Intent-Driven RouterAgent & EventBus Handoff Migration
  - Replaced hardcoded `.m4a`/`.pdf` routing rules in `inbox_daemon.py`
  - Upgraded `RouterAgent` to parse intents and generate dynamic skill chains
  - Implemented `TaskQueue` success listener to emit `PipelineCompleted` on `EventBus`
  - Configured `RouterAgent` to auto-enqueue subsequent skills for completely autonomous end-to-end workflows
  - Standardized `manifest.py` across all skills

- [x] 2026-04-19: Final Sign-off (v0.9.0) — Engineering documentation pass
  - `CHANGELOG.md` — v0.9.0 release block written
  - `memory/ARCHITECTURE.md` — full English rewrite; all new components documented
  - `memory/HANDOFF.md` — system state table + startup commands updated
  - All stale references to `web_ui/`, `note-generator`, `smart-highlighter` removed

- [x] 2026-04-19: Pre-flight Execution Sandbox — 12/12 import checks PASSED
  - Renamed `note-generator` → `note_generator`, `smart-highlighter` → `smart_highlighter`
  - Created `skills/__init__.py` + sub-package `__init__.py` files
  - Fixed `core/cli_runner.py` and `core/inbox_daemon.py` bare imports → `from core.path_builder`
  - Fixed `p05_synthesis.py` and `p03_synthesis.py` output path: `data/raw/` → `data/wiki/`
  - Added `watchdog>=4.0.0` and `requests>=2.31.0` to `requirements.txt`
  - Removed `flask>=3.0.0` from `requirements.txt`; installed `watchdog 6.0.0`

- [x] 2026-04-19: Phase 6 Final Cleanup
  - Removed Flask Web UI — orchestration now native to Open Claw
  - Fixed `SyntaxError` + duplicate method + wrong output path in `p05_synthesis.py`
  - Upgraded `inbox_daemon` to recursive subject-folder routing with triple PDF modes
  - Created `core/inbox_config.json` with 42 routing rules + inline descriptions
  - Created `skills/inbox_manager/` skill with CLI for runtime rule management

- [x] 2026-04-19: Antigravity Deep Thought Hotfixes (P0/P1/P2)
  - `inbox_daemon`: 300 s timeout + `stop_event` guard; debounce via `threading.Event`
  - `state_manager`: `fcntl.flock` to prevent concurrent JSON corruption
  - `cli_runner`: `PathBuilder` path resolution hardened

- [x] 2026-04-19: Full 4-Skill WebUI + CLI Integration
  - `core/cli_runner.py` (SkillRunner service layer)
  - `execution_manager.py` — Job Queue + same-skill deduplication
  - Extended `smart_highlighter` and `note_generator` CLIs with `--input-file` / `--output-file`

- [x] 2026-04-19: `smart_highlighter` and `note_generator` extracted as standalone skills

- [x] 2026-04-19: Global `.md` documentation update pass
- [x] 2026-04-19: Global `memory/` directory established (monorepo root + sandbox)
- [x] 2026-04-19: `ops/check.sh` quality gate created

- [x] 2026-04-18: `CODING_GUIDELINES.md` v3.0.0 consolidated and published
- [x] 2026-04-18: `INFRA_SETUP.md` updated to Version 9
- [x] 2026-04-18: `doc_parser` phase naming refactored (`p01a` → `p00a`, etc.)
- [x] 2026-04-18: `.gitignore` updated to exclude runtime files

- [x] 2026-04-15: `core/` shared framework established
- [x] 2026-04-15: `audio_transcriber` refactored to 6-phase MLX-Whisper pipeline
- [x] 2026-04-15: `doc_parser` 7-phase pipeline implemented
