# TASKS.md — Task Tracker

> **Last Updated:** 2026-05-08 (V9.6 — Synthesis Pipeline CLI Standardisation & DAG Hardening)

---

## 🔴 High Priority (阻斷性問題 / 核心功能)

*(None currently)*

---

## 🟡 Medium Priority (優化 / 非緊急功能)

- [ ] Review synthesis output quality in Obsidian: `data/note_generator/output/助人歷程/` — verify Mermaid renders, images display, no `<think>` tags
- [ ] Run full batch synthesis test: `run_all.py --subject 助人歷程 --force` for both skills (confirm DAG `❌ 0/5` → `✅ 5/5`)
- [ ] Populate `tests/` with E2E and integration test stubs per CODING_GUIDELINES §11.2
- [ ] Run live end-to-end pipeline test: `.m4a` → `data/wiki/`
- [ ] Rebuild ChromaDB index and validate a Telegram RAG query with `gemma4:e4b`
- [ ] Phase B (Memory & Graph RAG): ChromaDB + NetworkX deep integration

---

## 🟢 Low Priority (技術債 / 探索性研究)

- [ ] Register any future OCR service in `BOOTSTRAP.md` if/when needed
- [ ] Evaluate `CONTRIBUTING.md` guidelines if workspace becomes multi-contributor

---

## ✅ Completed

- [x] 2026-05-08: V9.6 Synthesis Pipeline CLI Standardisation & DAG Hardening
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
  - Created `open-claw-sandbox/docs/MODEL_SELECTION.md` per-skill model registry
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
