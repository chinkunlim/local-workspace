# TASKS.md — Task List

> **Last Updated:** 2026-04-19
> **Maintained by:** Current working agent — update on every state change

---

## 🔴 High Priority

*(None currently)*

---

## 🟡 Medium Priority

- [ ] Populate `tests/` with E2E and integration test stubs per CODING_GUIDELINES §11.2
- [ ] Run live end-to-end pipeline test: `.m4a` → `data/wiki/` (confirm all 6 phases)
- [ ] Rebuild ChromaDB index and validate a Telegram RAG query

---

## 🟢 Low Priority

- [ ] Register any future OCR service in `BOOTSTRAP.md` if/when needed
- [ ] Evaluate `CONTRIBUTING.md` guidelines if workspace becomes multi-contributor

---

## ✅ Completed

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
