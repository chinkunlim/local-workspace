# TASKS.md — Task List

> **Last Updated:** 2026-04-19
> **Maintained by:** Current working agent — update on every state change

---

## 🔴 High Priority

*(None currently)*

---

## 🟡 Medium Priority

- [ ] Add `tests/` directory structure per §11.2 (E2E + integration test stubs)

---

## 🟢 Low Priority

- [ ] Register OCR service in `BOOTSTRAP.md` if/when needed
- [ ] Evaluate adding `CHANGELOG.md` at workspace root (per §12.3)
- [ ] Consider `CONTRIBUTING.md` if workspace becomes multi-contributor

---

## ✅ Completed

- [x] 2026-04-19: Pre-flight Execution Sandbox — 12/12 import checks PASSED
  - Renamed `note-generator` → `note_generator`, `smart-highlighter` → `smart_highlighter`
  - Created missing `__init__.py` for skills/, note_generator/, smart_highlighter/ packages
  - Fixed `core/cli_runner.py` and `core/inbox_daemon.py` bare imports → `from core.path_builder`
  - Fixed `doc-parser/p03_synthesis.py` infinite re-ingestion loop (raw → wiki)
  - Added `watchdog>=4.0.0` and `requests>=2.31.0` to requirements.txt
  - Removed stale `flask` from requirements.txt (Web UI removed)
  - Installed watchdog 6.0.0 into active Python environment

- [x] 2026-04-19: Phase 6 Final Cleanup & Stabilization
  - Removed Flask Web UI — now fully Open Claw native
  - Fixed critical SyntaxError + duplicate method + wrong output path in `p05_synthesis.py`
  - Upgraded inbox_daemon to recursive subject-folder routing with triple PDF modes
  - Created `core/inbox_config.json` with 42 routing rules + inline descriptions
  - Created `inbox-manager` skill with CLI for rule management
  - Full MD documentation update pass
  - GitHub sync

- [x] 2026-04-19: Antigravity Deep Thought Hotfixes (P0/P1/P2)
  - P0: inbox_daemon HTTP-first trigger → WebUI Job Queue (OOM 防護)
  - P0: _wait_and_trigger 300s 超時 + stop_event (殭屍執行緒修復)
  - P0: debounce 改用 threading.Event 修復 dead code
  - P0: state_manager fcntl.flock 防止 JSON 並發損毀
  - P1: ExecutionManager 寫入 .rerun_state.json (消除 Silent Failure)
  - P2: cli_runner 改用 PathBuilder 路徑解析
  - start.sh: INFRA_DIR 路徑修正 + Dashboard 60s 超時 + 名稱更新
- [x] 2026-04-19: Full 4-Skill WebUI+CLI Integration
  - Created `core/cli_runner.py` (SkillRunner Service Layer)
  - Upgraded `execution_manager.py` to Job Queue + same-skill dedup
  - Added `/api/highlight`, `/api/synthesize`, `/api/queue`, `/api/status/skills` routes
  - Extended `smart-highlighter` and `note-generator` CLI with `--input-file`/`--output-file`
- [x] 2026-04-19: Extracted `smart-highlighter` and `note-generator` as standalone skills
- [x] 2026-04-19: 全域 .md 文件更新（README, TOOLS, HANDOFF, TASKS, .claude_profile）
- [x] 2026-04-19: 全域 `memory/` 目錄建立（monorepo root + sandbox）
- [x] 2026-04-19: 全域 `ops/check.sh` 建立
- [x] 2026-04-18: `pyproject.toml` moved to workspace root
- [x] 2026-04-18: `.pre-commit-config.yaml` moved to workspace root
- [x] 2026-04-18: `.editorconfig` created at workspace root
- [x] 2026-04-18: `ops/migrate_data_layout.py` deleted
- [x] 2026-04-18: `CODING_GUIDELINES_FINAL.md` v3.0.0 consolidated and published
- [x] 2026-04-18: `AI_Master_Guide_Final.md` updated to Version 9
- [x] 2026-04-18: doc-parser phase naming refactored (p01a→p00a, etc.)
- [x] 2026-04-18: `.gitignore` updated to exclude runtime files
- [x] 2026-04-15: `core/` shared framework established
- [x] 2026-04-15: audio-transcriber refactored to 6-phase MLX-Whisper pipeline
- [x] 2026-04-15: doc-parser 7-phase pipeline implemented
