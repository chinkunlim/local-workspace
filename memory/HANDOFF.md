# HANDOFF.md — Session Handoff Record

> **Last Updated:** 2026-06-03
> **System Status:** 🟢 Stable / Production-Ready (V9.26 — GC Thread & Soft-Delete Architecture)

---

## Current Session (2026-06-03 — V9.26 GC Thread & Soft-Delete Architecture)

**Date:** 2026-06-03

- [x] **Garbage Collection (GC) Soft-Delete System**: Transformed the pipeline's destructive file handling into a non-destructive 24-hour grace period system. Replaced `os.remove()` and `shutil.rmtree()` in `inbox_daemon` with soft-delete `deleted_at` markers injected into `state.json`.
- [x] **Background GC Thread**: Deployed a persistent background thread (`_gc_loop`) within `inbox_daemon` that sweeps expired Soft-Delete markers every 5 minutes and safely rotates orphaned `output/` directories to `data/.trash/`.
- [x] **Cross-Skill Invalidation Protocol**: Empowered `inbox_daemon` to actively intercept updates to upstream skill inputs (e.g., `doc_parser/input/`) and automatically invalidate downstream state caches (e.g., stripping the P3 Docling dependency flag in `proofreader`) to trigger autonomous re-pairing and LLM processing.
- [x] **Event-Driven File Tracking**: Extended `inbox_daemon`'s watchdog to detect `FileDeletedEvent` and `FileMovedEvent` directly from the filesystem, ensuring UI/Finder actions instantly reflect in the system state.
- [x] **Interactive CLI Safety Check**: Enhanced cleanup scripts (`cleanup_orphans.py`) with mandatory `(y/N)` prompt validation for operational safety.

---

## Previous Session (2026-06-03 — V9.25 Semantic Matcher Fix & Doc Parser DPI Boost)

**Date:** 2026-06-03

- [x] **Semantic Matcher Hallucination Fix**: Constrained `match_count=1` per chunk in `core/ai/semantic_matcher.py` and implemented partial string matching (`filename in raw_text`) before invoking the LLM, effectively preventing N-to-N matching hallucinations caused by overly eager prefix parsing.
- [x] **Doc Parser High-Res Image Pipeline**: Upgraded `Phase1aPDFEngine` to extract cropped images at 600 DPI (previously 300) for enhanced clarity.
- [x] **Auto-Image Embedding**: Implemented automatic Markdown image tag (`![image](filename)`) injection during the `doc_parser` PDF extraction phase to eliminate the need for manual post-processing of reference graphics.
- [x] **Global Registry Patch**: Patched `doc_parser/run_all.py` to ensure successful registration with `GlobalRegistry`, preventing pipeline desync during cross-skill asset lookup.
- [x] **System Logic Documentation**: Addressed user inquiries regarding `inbox_daemon` behavior and `StateManager` tracking, affirming that dropping files directly into `skills/audio_transcriber/input/` successfully triggers local execution without disrupting global pipeline routing.

---

## Previous Session (2026-05-29 — Log Recovery & Pipeline State Stabilization)

---

## Previous Session (2026-05-26 — Phase 7: Architecture Decoupling & Inversion of Control)

**Date:** 2026-05-26

- [x] **Architecture Discovery**: Mapped `core/orchestration`, `core/state`, and `core/ai` modules. Identified the "God Object" anti-pattern in `StateManager` and hardcoded routing logic in `RouterAgent`.
- [x] **Decoupling Roadmap**: Formulated a 3-phase architectural refactoring plan in `implementation_plan.md` to shift phase/routing configuration from hardcoded python lists to `SKILL.md` (YAML Frontmatter).
- [x] **ADR-019**: Published architectural decision record for Dependency Inversion of StateManager and RouterAgent in `DECISIONS.md`.
- [x] **New AI Principle**: Added Architecture Analysis Protocol to `AI_PROFILE.md` (mandating markdown plan drafts before code execution).

---

## Previous Session (2026-05-25 — V9.20 Proofreader Optimization & Auto-Checklist Logging)

**Date:** 2026-05-25

- [x] **Proofreader Model Unloading Optimization**: Refactored `p01_doc_proofread.py`, `p02_transcript_proofread.py`, and `p03_doc_completeness.py` to track loaded models and unload them at the end of the phase instead of per-file, significantly reducing I/O overhead for batch operations.
- [x] **Proofreader Reference Tracking**: Updated reference data fetching logic in `proofreader` to track actual reference filenames used and inject them into `note_tag` (e.g., `📚 參考: L03_raw_extracted.md`).
- [x] **Automated HITL Log Extraction**: Enhanced `PipelineBase.process_tasks()` to automatically intercept `HITLPendingInterrupt` exceptions and seamlessly write the Trace ID and pause reason into the task's `note_tag`. No manual per-skill log parsing is needed anymore.
- [x] **Legacy State Migration**: Created `update_state_from_logs.py` to extract historical `audio_transcriber` VAD/language warnings and `doc_parser` HITL traces into their `.pipeline_state.json` respectively.
- [x] **Inbox Daemon Clarification**: Updated `inbox_daemon.py` operation guidelines to clarify using `--scan-only` for direct execution without leaving a persistent background listener.

---

## Previous Session (2026-05-24 — V9.19 VAD Safety Limits & Global Clear Flag)

**Date:** 2026-05-24

- [x] **VAD Silence Removal Safety Limit**: Configured `vad_max_removal_ratio` in `audio_transcriber` config to `0.10` (10%). Modified `vad_preprocess()` in `p01_transcribe.py` to activate a safety fallback that ignores VAD if more than 10% of the audio is removed.
- [x] **Silence Ratio Note Tag Logging**: Integrated the actual silence removal ratio (e.g., `VAD 移除靜音 XX.X%`) into the pipeline state checklist via `StateManager.update_task` `note_tag` argument.
- [x] **Global `--clear` CLI Flag**: Implemented the `--clear` / `-c` CLI argument universally across all 12 skills.
  - Added `StateManager.clear_progress()` to reset all phase records to `⏳` and wipe hashes/notes/checkpoints.
  - Injected `include_clear=True` into `core/cli/cli.py` `build_skill_parser()`.
  - Added fast early-exit `--clear` block in all standalone skill orchestrator `run()` methods (Batch A).
  - Integrated native `--clear` processing in `PipelineBase.run_skill_pipeline()` for unified skills (Batch B).

---

## Previous Session (2026-05-23 — V9.18 OpenClaw Native Pipeline Skills Integration)

**Date:** 2026-05-23

- [x] **ADR-013 OpenClaw Integration**: Unified the Telegram bot architecture by enabling the OpenClaw Agent to natively discover and trigger heavy Python ML pipelines.
- [x] **Symlink Security Bypass**: Hard-copied `openclaw-sandbox/skills/*/SKILL.md` to `~/.openclaw/skills/` to bypass the OpenClaw `symlink-escape` security block.
- [x] **Deprecated bot_daemon.py**: Eliminated the need for a separate pipeline Telegram bot. OpenClaw now handles all NLP requests and file routing via its native interface.

---

## Previous Session (2026-05-23 — V9.17 Coding Guidelines Full Compliance)

- [x] **Syntax Fix**: Repaired unclosed parenthesis in `gemini_verifier_agent/p01_ai_debate.py` (`super().__init__` call missing `)`) — was causing Ruff/Mypy parse failure across all 3 checks.
- [x] **OllamaClient Refactor**: Removed manual `OllamaClient()` instantiation in 2 skill phases:
  - `knowledge_compiler/p02_extract_graph.py` — now reuses `self.llm` inherited from `PipelineBase`
  - `doc_parser/p00b_png_pipeline.py` — now reuses `self.llm` inherited from `PipelineBase`
- [x] **print() → Structured Logging Migration** (§8.1 compliance): Migrated 14 bare `print()` calls in production methods to `self.info/self.error/self.warning/self.log`:
  - `student_researcher/p01_claim_extraction.py` (4 calls)
  - `student_researcher/p02_synthesis.py` (6 calls)
  - `gemini_verifier_agent/p01_ai_debate.py` (4 calls)
  - Note: `print()` in `if __name__ == "__main__":` CLI blocks are explicitly excluded (acceptable per convention)
- [x] **Quality Gate Verified**: `./ops/check.sh` ✅ Ruff lint, ✅ Ruff format, ✅ Mypy 0 errors (147 files)
- [x] **Test Suite**: `pytest` ✅ 22 passed, 5 skipped (34.88s)
- [x] **Committed**: `fix(skills): migrate bare print() to structured logging; fix syntax error; remove manual OllamaClient`
- [x] **Global Documentation Sync (V9.17)**: Fully audited all Markdown files. Synced `docs/ARCHITECTURE.md`, `docs/INDEX.md`, `docs/STRUCTURE.md`, `USER_MANUAL.md`, and created missing architecture docs for `proofreader`, `student_researcher`, `academic_library_agent`, and `gemini_verifier_agent` to enforce SSoT compliance.

---

## Final Sign-off Summary (V9.14 — Proofreader HITL Pipeline Integration)

**Date:** 2026-05-22
**Milestone:** V9.14 — Proofreader HITL Pipeline Integration

- [x] **HITL Pipeline Pause/Resume**: Integrated `proofreader` fully into the automated `audio_transcriber` and `doc_parser` chains. The `RouterAgent` now detects when the next skill is `proofreader`, pauses execution by writing to `pending_chains.json`, and stops propagation instead of blindly pushing to the background task queue.
- [x] **Watchdog Pipeline Resume**: Enhanced `inbox_daemon.py` to watch for saved files in `data/proofreader/output/04_final_verified/`. Upon detection, it loads the saved state and publishes a `PipelineCompleted` event to automatically resume `smart_highlighter`.
- [x] **Dashboard Skip & Forward**: Added a new API endpoint `/api/skip` and a UI button in the `proofreader` dashboard to allow users to force-skip the manual review process, copying the raw AI output directly to `04_final_verified` to resume the pipeline instantly.
- [x] **SkillRunner Route Resolution**: Updated `cli_runner.py` to correctly resolve input/output paths when `current_skill` is `proofreader` or `smart_highlighter`, ensuring seamless cross-skill handoffs.

> [!NOTE]
> The `openclaw.json` `agents.defaults.workspace` still references the old `open-claw-sandbox` path. The sandbox was renamed to `openclaw-sandbox/`. This may cause issues if OpenClaw tries to access the workspace. Consider updating via `openclaw configure` or `openclaw config set`.

---

## Previous Session (V9.10 — 2026-05-13)

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
| Skill package names | `note_generator`, `smart_highlighter` (underscore — enforced §5.7) |
| Skill entry points | All skills use `scripts/run_all.py` (enforced §5.8) |
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

1. **Phase 1: Decouple StateManager**: The implementation plan is ready (`implementation_plan.md`). Start by modifying `core/orchestration/skill_registry.py` to parse custom frontmatter arrays, then refactor `StateManager.__init__` to load them.
2. **Phase 2: Decouple RouterAgent**: Shift I/O contracts into `SKILL.md` and remove hardcoded routing paths in `RouterAgent._on_pipeline_completed`.
3. **Conduct End-to-End Execution Walkthrough**: Perform a real-world validation run by placing a raw audio (`.m4a`) or PDF (`.pdf`) into `data/raw/<Subject>/`, checking that the pipeline pauses at the `proofreader` dashboard, propagates alerts via Telegram, and successfully resumes either through manual confirmation or the dashboard `/api/skip` endpoint.
4. **Execute Quality Gates**: Run the automated gate sweeps (`cd openclaw-sandbox && ./ops/check.sh`) periodically during routine feature iterations to prevent Ruff/Mypy drift.
5. **Phase B (Memory & Graph RAG)**: Transition to the integration of ChromaDB vectors and NetworkX relationships to manage multi-level semantic indexing.

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
| 2026-05-30 | Telegram Bot UX & System Cleanup | Fixed AppleScript AppleEvent hijacking for `/resume` via native Terminal tab instantiation; purged `TestSubject` & `Default` test assets globally; cleaned residual dummy states from all `.pipeline_state.json` caches. |
| 2026-05-29 | Data Restoration & Pipeline Clean Reset | Restored `audio_transcriber` `03_merged` files from `<Original>` blocks; purged polluted downstream `proofreader` and `smart_highlighter` inputs. |
| 2026-05-29 | V9.23 Eager Execution & HITL Verification Fixes | Fixed RouterAgent eager chain index; patched InboxDaemon `resume_chain` to retain proofreader context; updated `check_status.py` to order and expose empty states (0/0) for pipeline clarity. |
| 2026-05-29 | V9.22 Orchestration Hardening & Telegram GUI | AppleScript terminal reuse for `/resume`, callback queries fixed, timeout removed, and dynamic `/status` hiding implemented. |
| 2026-05-26 | V9.21 Phase 6 Architectural Standardization | Replaced polling with `FileStabilityPoller`, mandated editable installs, hardened LLM session unloading, added E2E routing tests. |
| 2026-05-22 | V9.16 Dual-Track 5-Layer Architecture | Reorganized system workflows into a clean 5-layer design with Parallel Dual-Track data flows (L3->L5 bypass, and L3->L4->L5 research route). Connected TG Bot directly to Layer 4, moved note_generator to Layer 3, and updated docs/ARCHITECTURE.md and system_workflow_guide.md. |
| 2026-05-22 | V9.15 Memory Hardening & SSoT Verification | Verified core VLM & HITL implementation, synced ADRs, resolved Coding Guidelines numbering, and hardened sequential VLM/HITL exceptions invariants. |
| 2026-05-22 | V9.14 HITL Proofreader Pipeline Pause/Resume | Integrated `proofreader` via JSON state pause/resume, added Dashboard Force Skip button, added full watchdog resume loop. |
| 2026-05-22 | V9.13 Semantic Router & Idea Incubator | Added Phase 0 for semantic routing, dynamic Incubator tagging, fixed file handoffs in RouterAgent, mapped full 15-skill 5-layer architecture. |
| 2026-05-22 | V9.12 VLM Stability & HITL Fixes | Set Semaphore(1) for VLM vision to prevent OOM, fixed HITLPendingInterrupt propagation, integrated Telegram notification natively, added E2E test stubs |
| 2026-05-13 | V9.11 RouterAgent Refactor & PPTX Image Extraction | Replaced hardcoded routing with inbox_config.json; implemented python-pptx image extraction in Phase 0c; resolved PPTX placeholders in figure_list |
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
