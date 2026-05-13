# HANDOFF.md — Session Handoff Record

> **Last Updated:** 2026-05-13
> **System Status:** 🟢 Stable / Production-Ready (V9.11 — RouterAgent Config-Driven Routing Refactor + PPTX Image Extraction)

---

## Current Session (2026-05-13 — RouterAgent Refactor + PPTX Image Extraction)

**Date:** 2026-05-13

- [x] **RouterAgent config-driven routing (refactored)**: Replaced hardcoded `_ROUTING_TABLE` global dict with a `_build_routing_table()` instance method. Now reads `core/config/inbox_config.json` at init time. Adding a new file format requires only editing JSON, zero Python changes. `_INTENT_ROUTES` (e.g. `.pdf:study`) remain in code as they are orchestration logic, not file-type config. See ADR-013.
- [x] **`inbox_daemon.py` dead code cleanup**: Removed `_load_config()` method (31 lines) and its `self.routing_rules`/`self.pdf_routing_rules` dicts. Routing is now entirely owned by `RouterAgent._build_routing_table()`.
- [x] **PPTX embedded image extraction**: Added `_extract_pptx_images()` to `Phase0cMarkItDown`. Uses python-pptx (bundled with `markitdown[pptx]`) to extract image blobs from all slides, saved to the same directory as `raw_extracted.md`. Filename convention matches MarkItDown's internal convention exactly (`re.sub(r"\W", "", shape.name) + ".jpg"`), so all `![...](filename)` references in the Markdown resolve without modification.
- [x] **`figure_list.md` updated**: Now lists actual extracted image filenames from PPTX blobs instead of a generic placeholder row.
- [x] **E2E verified**: `L12_GLP-1 agonists 2026_slide.pptx` processed — 5 images extracted (Picture2.jpg / Picture3.jpg / Picture9.jpg / Picture11.jpg / Picture12.jpg), all referenced correctly in raw_extracted.md.
- [x] **doc_parser/docs/ARCHITECTURE.md V4.0**: Pipeline DAG diagram updated to show 3-branch routing (Office / PDF / Image); phases directory listing updated with `p00c_markitdown.py`; state tracking phases updated.
- [x] **doc_parser/docs/DECISIONS.md**: Added PPTX image extraction ADR (co-location rationale + MarkItDown naming convention match).

> [!NOTE]
> The `openclaw.json` `agents.defaults.workspace` still references the old `open-claw-sandbox` path. The sandbox was renamed to `openclaw-sandbox/`. This may cause issues if OpenClaw tries to access the workspace. Consider updating via `openclaw configure` or `openclaw config set`.


---

## Final Sign-off Summary

**Date:** 2026-05-13
**Milestone:** V9.10 — MarkItDown Integration, RouterAgent Refactor & Proofreader DAG Fixes

- [x] **`correction_log.md` DAG Pollution Fix**: Added filter `if fname == "correction_log.md": continue` in Manual State Injection loops inside `p02_transcript_proofread.py`, `p03_doc_completeness.py`, `proofreader/run_all.py`, and `core/state/state_manager.py`. Prevents log files from being treated as processable pipeline entries, which caused inflating DAG counts and P2 resetting across runs.
- [x] **Phase 0c MarkItDown — PPTX/DOCX/XLSX Support**: New `Phase0cMarkItDown` (`p00c_markitdown.py`) added to `doc_parser`. Uses `markitdown[pptx,docx,xlsx]` to convert Office files to Markdown with identical output interface as `Phase1aPDFEngine`. PPTX speaker notes preserved as `### Notes:` blocks.
- [x] **doc_parser DAG masking for 3 file-type branches**: Updated `doc_parser/run_all.py` to mask phases by file type — PDF (skip p0c+p0b), Image (skip all text phases), Office (skip all PDF-specific phases).
- [x] **`state_manager.py` extended**: `PHASES_PDF` now includes `p0c`; `file_ext` now includes `.pptx`, `.docx`, `.xlsx`; `correction_log.md` filtered in `sync_physical_files`.
- [x] **RouterAgent config-driven routing**: Replaced hardcoded `_ROUTING_TABLE` dict with `_build_routing_table()` that dynamically reads `inbox_config.json`. Adding a new file type now only requires editing JSON, not Python code.
- [x] **`inbox_daemon.py` cleanup**: Removed duplicate `_load_config()` method — routing now owned entirely by `RouterAgent._build_routing_table()`.
- [x] **`inbox_config.json` extended**: Added `.pptx`, `.docx`, `.xlsx` to `pdf_knowledge` routing group.
- [x] **CODING_GUIDELINES §5.4 extended**: Added "Log File Filter Invariant" rule — all state population loops must skip `correction_log.md`.
- [x] **ADR-013**: Documented config-driven routing design in `memory/DECISIONS.md`.
- [x] **`skills/doc_parser/docs/DECISIONS.md`**: Added MarkItDown integration ADR with full rationale (Why NOT MarkItDown for audio, PPTX vs Docling trade-offs).
- [x] **Prompt Engineering**: Improved End-of-Session and Startup prompts — added dynamic MD discovery, explicit `correction_log.md` filter rationale per invariant, corrected Step 4/5 order explanation.

---

## Previous Session (V9.9 — 2026-05-13)

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

1. **Run live E2E test**: Place `.m4a` + `.pdf` + `.pptx` into `data/raw/助人技巧/` — confirm full `audio_transcriber` → `doc_parser` → `proofreader` chain completes with DAG showing stable counts (no correction_log.md pollution).
2. **Proofreader P2/P3 validation**: Verify Phase 2 runs correctly with the DAG pollution fix; confirm DAG counts remain stable across multiple runs.
3. **Fix `openclaw.json` stale workspace path**: Update `agents.defaults.workspace` from `open-claw-sandbox` → `openclaw-sandbox` via `openclaw configure`.
4. **Run full batch synthesis**: `uv run skills/note_generator/scripts/run_all.py --subject 助人技巧 --force`
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
| 2026-05-13 | V9.10 MarkItDown Integration, RouterAgent & DAG Fixes | Phase0cMarkItDown (PPTX/DOCX/XLSX); config-driven routing; correction_log pollution fix; ADR-013 |
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

