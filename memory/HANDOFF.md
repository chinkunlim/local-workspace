# HANDOFF.md — Session Handoff Record

> **Last Updated:** 2026-05-22
> **System Status:** 🟢 Stable / Production-Ready (V9.15 — Memory Hardening & SSoT Verification)

---

## Current Session (2026-05-22 — V9.15 Memory Hardening)

**Date:** 2026-05-22

- [x] **Historical Audit & Code Verification**: Verified and synced core codebase enhancements, ensuring VLM Vision implements sequential `Semaphore(1)` constraint, OCR Gate correctly propagates `HITLPendingInterrupt`, and Telegram dispatch natively integrates without TODO regression risk.
- [x] **Architecture Decisions Record (ADR) Sync**: Documented ADR-015 (VLM Concurrency and HITL Telegram bot) and ADR-016 (Non-blocking proofreader and Watchdog resumer) inside `memory/DECISIONS.md`.
- [x] **Guidelines Hardening**: Hardened `docs/CODING_GUIDELINES.md` to v4.2.0. Resolved section 5 duplicate subsection numbers. Appended §5.11 (VLM Concurrency Limit Invariant) and §5.12 (HITL Interrupt Propagation Invariant) as permanent coding requirements.
- [x] **Rules & Directory Map Sync**: Updated `memory/PROJECT_RULES.md` environment hardware constraints to enforce sequential VLM executions. Synchronized `docs/STRUCTURE.md` registry mapping and updated timestamps to `2026-05-22`.
- [x] **Handoff Reconciliation**: Reconciled the master handoff protocol to establish the exact post-audit status.

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

1. **Conduct End-to-End Execution Walkthrough**: Perform a real-world validation run by placing a raw audio (`.m4a`) or PDF (`.pdf`) into `data/raw/<Subject>/`, checking that the pipeline pauses at the `proofreader` dashboard, propagates alerts via Telegram, and successfully resumes either through manual confirmation or the dashboard `/api/skip` endpoint.
2. **Execute Quality Gates**: Run the automated gate sweeps (`cd openclaw-sandbox && ./ops/check.sh`) periodically during routine feature iterations to prevent Ruff/Mypy drift.
3. **Phase B (Memory & Graph RAG)**: Transition to the integration of ChromaDB vectors and NetworkX relationships to manage multi-level semantic indexing.
4. **Fix `openclaw.json` Stale Workspace Path**: Clean up `agents.defaults.workspace` config pointers referencing the legacy sandbox directory.

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
| 2026-05-22 | V9.15 Memory Hardening & SSoT Verification | Verified core VLM & HITL implementation, synced ADRs, resolved Coding Guidelines numbering, and hardened sequential VLM/HITL exceptions invariants. |
| 2026-05-22 | V9.14 HITL Proofreader Pipeline Pause/Resume | Integrated `proofreader` via JSON state pause/resume, added Dashboard Force Skip button, added full watchdog resume loop. |
| 2026-05-22 | V9.13 Semantic Router & Idea Incubator | Added Phase 0 for semantic routing, dynamic Incubator tagging, fixed file handoffs in RouterAgent, mapped full 15-skill 6-layer architecture. |
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
