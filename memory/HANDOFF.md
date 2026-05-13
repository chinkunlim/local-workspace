# HANDOFF.md — Session Handoff Record

> **Last Updated:** 2026-05-13
> **System Status:** 🟢 Stable / Production-Ready (V9.9 — Doc-Parser & Proofreader Pipeline Standardization)

---

## Current Session (2026-05-13 — Git Recovery & OpenClaw Architecture Investigation)

**Date:** 2026-05-13

- [x] **Restored `manual/*.docx` files**: 8 `.docx` files deleted in commit `53bf7e3` were recovered from git history via `git checkout 10251a4 -- "manual/*.docx"` and staged for commit.
- [x] **Investigated `openclaw skills` not showing project skills**: Diagnosed root cause — `openclaw skills` CLI only lists OpenClaw's own bundled/managed skills. The project's Python pipeline skills (`audio_transcriber`, `doc_parser`, etc.) are managed by `core/orchestration/skill_registry.py`, a completely separate system.
- [x] **ADR-012 documented**: Formalised the two-system architecture in `memory/DECISIONS.md` to prevent future confusion.
- [x] **Confirmed `openclaw.json` workspace**: `agents.defaults.workspace` correctly points to `/Users/limchinkun/Desktop/local-workspace/open-claw-sandbox` (note: old path; sandbox is now at `openclaw-sandbox/`). Functional but the path is stale.
- [x] **Cleaned up test artifacts**: Removed `openclaw-sandbox/skills/audio-transcriber-test/` (created during investigation).

> [!NOTE]
> The `openclaw.json` `agents.defaults.workspace` still references the old `open-claw-sandbox` path. The sandbox was renamed to `openclaw-sandbox/`. This may cause issues if OpenClaw tries to access the workspace. Consider updating via `openclaw configure` or `openclaw config set`.

---

## Final Sign-off Summary

**Date:** 2026-05-13
**Milestone:** V9.9 Doc-Parser & Proofreader Pipeline Standardization


- [x] **`phase_key` Alignment (doc_parser P1c & P1d)**: Fixed `phase_key` mismatches — previously causing completed tasks to be re-queued endlessly.
- [x] **NameError Fix (doc_parser P1d)**: Declared missing `pdf_path` variable in `_process_file` to prevent crash during EventBus handoff.
- [x] **GlobalRegistry Deadlock Fix**: Changed `threading.Lock()` → `threading.RLock()` — eliminated silent hang in `get_asset_paths()` recursive lock acquisition.
- [x] **Manual State Injection (proofreader)**: Replaced `sync_physical_files()` in `p02` and `p03` with manual directory iteration that preserves `⏭️` masks.
- [x] **Continuous Masking**: Added `else:` branches in all proofreader phases and `run_all.py` to enforce masks on existing state entries.
- [x] **RouterAgent Proofreader Wakeup Fix**: Corrected wakeup cmd path from individual phase script → `scripts/run_all.py`.
- [x] **Proofreader Dashboard in start.sh**: Port `8081`, auto-opens browser; integrated into `stop.sh` cleanup.
- [x] **inbox_daemon path fix**: Corrected `core/inbox_daemon.py` → `core/services/inbox_daemon.py` in both `start.sh` and `stop.sh`.
- [x] **CODING_GUIDELINES §5.4**: Documented `sync_physical_files()` vs Manual State Injection invariant.
- [x] **Full Pipeline Architecture Review**: Confirmed audio_transcriber → doc_parser → proofreader handoff via EventBus + GlobalRegistry + session_manifest is intact end-to-end.

---

## Previous Session (V9.8 — 2026-05-12)

**Milestone:** V9.8 uv-Native Toolchain Migration

- [x] **uv-Native Toolchain Migration**: Removed `requirements.txt` and `requirements.in`. All 160+ dependencies now managed exclusively via `pyproject.toml` and `uv.lock`. Added `[project]` table to enable `uv add`.
- [x] **Dev Dependencies via uv**: `ruff`, `mypy`, `pytest` added as dev dependencies (`uv add --dev`).
- [x] **`check.sh` uv-Hardened**: Updated `openclaw-sandbox/ops/check.sh` to call `uv run ruff` and `uv run mypy` instead of bare commands, eliminating the `command not found` failure on clean environments.
- [x] **Syntax Bug Fixes**: Repaired two broken Python files (`academic_library_agent/p01_search_literature.py`, `gemini_verifier_agent/p01_ai_debate.py`) that had dangling indentation and undefined variable references causing Mypy and Ruff parse failures.
- [x] **Type Error Fixes**: Fixed 4 Mypy type errors in `core/state/global_registry.py` (`_memory_cache` annotation) and corrected `_debate_gemini` return type.
- [x] **Quality Gate**: `check.sh` now passes — ✅ Ruff lint, ✅ Ruff format, ✅ Mypy (0 errors, 143 files).
- [x] **MLX-Whisper Model Download**: Triggered `hf download mlx-community/whisper-large-v3-mlx` to `models/` with `HF_HOME` sandboxed inside the project. Faster-Whisper `medium` model also downloaded.

---

## Current System State
- [x] **Proofreader Orchestrator Refactoring**: Upgraded `proofreader` to use `PipelineBase`, adding an interactive CLI (`--force`, `--resume`, `--subject`) and DAG tracking dashboard mirroring other core skills.
- [x] **Per-file EventBus Handoff**: Refactored `audio_transcriber`, `proofreader`, `note_generator`, and `smart_highlighter` to emit `PipelineCompleted` per-file rather than per-batch, enabling true asynchronous cross-skill pipelining.
- [x] **Dynamic Reference Fetching**: `proofreader` (p01, p02) now safely looks up reference doc paths via the `GlobalRegistry` instead of insecure path traversal.

- [x] **audio_transcriber `run_all.py` Import Fix**: Corrected stale import (`Phase2Proofread` → `Phase2GlossaryApply`) that caused `ModuleNotFoundError` on startup. Pipeline now runs end-to-end.
- [x] **smart_highlighter V2.0 — Orchestrator Architecture**: Renamed `highlight.py` → `run_all.py`. Implemented `SmartHighlighterOrchestrator` with DAG dashboard, `StateManager` tracking, `--force/--resume/--subject/--file` CLI, asset directory copying, and dual file/batch mode (mirrors `audio_transcriber`).
- [x] **note_generator V2.0 — Orchestrator Architecture**: Renamed `synthesize.py` → `run_all.py`. Implemented `NoteGeneratorOrchestrator` with identical DAG/CLI architecture. Added `strip_think_tags()` for reasoning model compatibility and `fix_mermaid_syntax()` for self-healing Mermaid output.
- [x] **StateManager — `raw_dir` Override**: Added optional `raw_dir` parameter so skills reading from cross-skill output paths (e.g., `proofreader/output`) can correctly report DAG file counts.
- [x] **StateManager — New Phase Registrations**: Added `PHASES_HIGHLIGHT = ['highlight']` / `PHASES_NOTE = ['synthesize']` with display labels `H1 (重點標記)` / `N1 (知識合成)`.
- [x] **highlight.py `skill_name` Bug Fix**: Corrected `skill_name="smart-highlighter"` (hyphen) to `skill_name="smart_highlighter"` (underscore) in old `highlight.py`. Config loading was silently failing.
- [x] **note_generator API Timeout**: Increased `timeout_seconds` from 600 → 1800 to support 8-model synthesis output.
- [x] **Both `manifest.py` updated**: `cli_entry` for both skills now points to `scripts/run_all.py`.
- [x] **CODING_GUIDELINES §5.5–5.8**: Documented four new invariants (skill_name convention, run_all.py naming, think-tag stripping, raw_dir override).
- [x] **check.sh**: ✅ All Passed — Ruff + Mypy (158 files, 0 errors).

- [x] **Phase A Performance Hardening (V9.1)**: `SqliteSemanticCache` in `llm_client.py`; Exponential Backoff in `task_queue.py`; Scheduler Queue Safety via `LocalTaskQueue`.
- [x] **Context-Aware Model Routing (V9.1)**: `RouterAgent` assigns `qwen3:14b` (high-complexity) or `qwen3:8b` (low-complexity) based on intent keywords.
- [x] **Quality-First Model Upgrade (V9.2)**: All skills upgraded to optimal models (see `docs/MODEL_SELECTION.md`). Key changes:
  - `note_generator`: `phi4-mini-reasoning` → `qwen3:14b` (active profile `qwen3_reasoning`)
  - `student_researcher`: `qwen3:8b` → `deepseek-r1:8b` (CoT claim extraction)
  - `knowledge_compiler`, `gemini_verifier_agent`, `academic_edu_assistant`, `academic_library_agent`, `interactive_reader`, `video_ingester`: `qwen3:8b` → `qwen3:14b`
  - `telegram_kb_agent`: `gemma4:e2b` → `gemma4:e4b`
- [x] **Ollama Model Cleanup**: Removed `deepseek-r1:14b` (9GB), `qwen2.5-coder:7b` (4.7GB), `llama3.1` (4.9GB) — saved 23.6GB.
- [x] **`docs/MODEL_SELECTION.md`**: Created complete per-skill model registry with primary/fallback models, rationale, and quick-switch instructions.
- [x] **All MD files updated**: `CHANGELOG.md`, `HANDOFF.md`, `TASKS.md`, `memory/DECISIONS.md`, `memory/ARCHITECTURE.md`, `feynman_simulator/SKILL.md`, `note_generator/docs/DECISIONS.md`.

---

## Current System State

| Attribute | Value |
| ---------------------- | -------------------------------------------------------------------------------- |
| Git | Clean — synced with `origin/main` |
| Ruff linting | ✅ All checks passed |
| Ruff format | ✅ 162 files clean |
| Mypy | ✅ 0 errors in 143 source files (`core/` + `skills/`) |
| Python version | `3.11` (pinned via `.python-version`) |
| Dependency manager | `uv` (exclusive) — `requirements.txt` removed |
| Ollama models | 9 models present (gemma4, llama3, llama3.2-vision, phi4-mini-reasoning, qwen3:8b, deepseek-r1:8b, gemma4:e2b, gemma4:e4b, nomic-embed-text) |
| MLX-Whisper model | `mlx-community/whisper-large-v3-mlx` — downloading to `models/` |
| Faster-Whisper model | `medium` — downloaded to `models/` |
| Skill package names | `note_generator`, `smart_highlighter` (underscore — enforced §5.5) |
| Skill entry points | All skills use `scripts/run_all.py` (enforced §5.6) |
| DAG Phases | `smart_highlighter`: H1 (重點標記); `note_generator`: N1 (知識合成) |
| note_generator timeout | 1800 seconds (supports 8-model synthesis) |
| Inbox routing | Intent-Driven via `RouterAgent` and `SkillRegistry` |
| Pipeline Handoff | Autonomous via `EventBus` (`TaskQueue` emits `PipelineCompleted`) |
| LLM Semantic Cache | `data/llm_cache.sqlite3` (SHA-256 keyed, `temperature=0` only) |
| Model Registry | `openclaw-sandbox/docs/MODEL_SELECTION.md` |
| Obsidian Vault | `openclaw-sandbox/data/wiki/` |
| ChromaDB index | `openclaw-sandbox/data/chroma/` (rebuilt by `telegram_kb_agent`) |
| Startup Protocol | `memory/STARTUP.md` (canonical prompt + 5-Phase process) |

---

## Standard Startup Sequence

```bash
# 1. Start all infrastructure services
./infra/scripts/start.sh

# 2. Verify services (optional)
curl http://localhost:11434/api/tags        # Ollama models
curl http://localhost:18789/health          # Open Claw API

# 3. Drop files into the Universal Inbox
# Place .m4a or .pdf under data/raw/<Subject>/
# The inbox_daemon will route and trigger pipelines automatically.

# 4. Query the knowledge base (via Open Claw / Telegram)
# "What did the lecture on cognitive psychology cover?"
# Open Claw dispatches telegram_kb_agent → ChromaDB → response
```

---

## Next Session Starting Point

1. **Run live E2E test**: Place a `.m4a` + matching `.pdf` into `data/raw/助人技巧/` and confirm the full chain: `audio_transcriber` → `doc_parser` → `proofreader` (P1 for docs, P2+P3 for audio) completes automatically.
2. **Proofreader P2/P3 validation**: Verify Phase 2 (Transcript Proofread) runs without the GlobalRegistry deadlock and correctly pulls doc reference text for cross-checking.
3. **Review Proofreader Dashboard**: Open `http://localhost:8081` and confirm AI-corrected files are visible for Human-in-the-Loop review.
4. **Run full batch synthesis**: `uv run skills/note_generator/scripts/run_all.py --subject 助人技巧 --force`.
5. Rebuild ChromaDB index: `uv run skills/telegram_kb_agent/scripts/indexer.py`
6. Populate `tests/` stub structure per CODING_GUIDELINES §11.2.

> **Startup Protocol**: Copy the prompt from `memory/STARTUP.md` at the start of every new conversation.

---

## Known Open Issues

- **None blocking.**
- `tests/` directory stubs are declared in `TASKS.md` but not yet populated (low priority).
- **`openclaw.json` stale workspace path**: `agents.defaults.workspace` still points to `/Users/limchinkun/Desktop/local-workspace/open-claw-sandbox` (old name). Sandbox is now at `openclaw-sandbox/`. Low priority until OpenClaw tries to resolve workspace files via CLI.

---

## Previous Sessions (Condensed)

| Date | Focus | Outcome |
| ---------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 2026-05-13 | Git Recovery & OpenClaw Architecture Investigation | Restored 8 `.docx` files from git; diagnosed `openclaw skills` two-system architecture; documented ADR-012 |
| 2026-05-13 | V9.9 Doc-Parser & Proofreader Pipeline Standardization | `phase_key` fixed; GlobalRegistry deadlock fixed; Manual State Injection for proofreader; Proofreader Dashboard in start.sh; inbox_daemon path corrected |
| 2026-05-12 | V9.8 uv-Native Toolchain Migration & Quality Gate | Removed `requirements.txt`; migrated to `uv add`; fixed `check.sh` to use `uv run`; fixed 3 syntax/type bugs; 0 errors in 143 files |
| 2026-05-10 | V9.7 Proofreader & Global Asset Registry | Implemented `GlobalRegistry`, per-file EventBus handoff, and `ProofreaderOrchestrator`. |
| 2026-05-08 | V9.6 Synthesis Pipeline CLI & DAG Standardisation | `smart_highlighter`/`note_generator` → `run_all.py` Orchestrators; DAG fixed; 4 new §5 invariants |
| 2026-05-07 | Advanced Prompt Engineering & Routing | Upgraded `note_generator` and `smart_highlighter` models; defined Parallel Extraction vs Synthesis architecture (ADR-011) |
| 2026-05-07 | Multi-Format Parse & Async Verification | Docling PDF/PNG fixed; Blocking Verification Gate replaced with Async Dashboard |
| 2026-05-05 | Full Mypy Compliance + AI Doc System Hardening | 0 type errors in 133 files; STARTUP.md created; Code Review Checklist added |
| 2026-05-05 | Audio Pipeline Pathing & Tech Stack Docs | Path traversal bugs fixed, VAD hardened, `OPENCLAW_TECH_STACK.md` created |
| 2026-05-04 | Quality-First Model Optimization (V9.2) | All skills upgraded to optimal models; 23.6GB Ollama cleanup; MODEL_SELECTION.md created |
| 2026-05-04 | Phase A Performance Hardening (V9.1) | SQLite cache, exponential backoff, scheduler queue safety |
| 2026-05-02 | Documentation SSoT Sync | `USER_MANUAL.md`, `STRUCTURE.md`, `DECISIONS.md` fully updated |
| 2026-05-01 | Intent-Driven Architecture Migration | `RouterAgent` + `EventBus` auto-handoff implemented; Inbox hardcoding removed |
| 2026-04-19 | Phase 6 Finalisation — Inbox routing + Web UI removal | `inbox_config.json`, `inbox_manager` skill, wiki output paths fixed |
| 2026-04-19 | Skill Extraction | `smart_highlighter`, `note_generator` extracted as standalone packages |
| 2026-04-18 | Monorepo restructure + CODING_GUIDELINES_FINAL v3.0.0 | All config files promoted to root; docs consolidated |
| 2026-04-15 | Core framework + dual-skill pipeline | `core/` shared framework; `audio_transcriber` + `doc_parser` fully operational |

