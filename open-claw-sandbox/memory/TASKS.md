# TASKS.md — Task List

> **Last Updated:** 2026-04-18
> **Maintained by:** Current working agent — update on every state change

---

## 🔴 High Priority

*(None currently)*

---

## 🟡 Medium Priority

- [ ] Verify Dashboard Review Board renders latest diff records correctly
- [ ] Confirm `logs/inbox_daemon.log` shows uninterrupted file-trigger events
- [ ] Add `tests/` directory structure per §11.2 (E2E + integration test stubs)

---

## 🟢 Low Priority

- [ ] Register OCR service in `BOOTSTRAP.md` if/when needed
- [ ] Evaluate adding `CHANGELOG.md` at workspace root (per §12.3)
- [ ] Consider `CONTRIBUTING.md` if workspace becomes multi-contributor

---

## ✅ Completed

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
