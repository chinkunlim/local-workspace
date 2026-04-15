# PROGRESS.md — Project Milestones

> [!TIP]
> 專案版本週期的行事曆與輝煌的里程碑。每一次的大型重構 (`Refactor`) 都被精確錨定在這裡。

## [2026-04-15] - Core Modularization & Dual-Skill Alignment (V7.2)
- **Milestone**: Aligned `voice-memo` and `pdf-knowledge` skills with strict OOP guidelines and extracted core utilities.
- **Status**: Stable.
- **Features**:
    - Extracted Map-Reduce text chunking from `phase5_synthesis.py` to `core/text_utils.py` for cross-skill usage.
    - Unified project-level coding guidelines (OOP, Emojis, Idempotency) explicit bounds on both skills without merging domain logic.
    - Introduced global `requirements.txt` and `bootstrap.sh` (macOS) to enforce dual-skill dependency stability seamlessly.

## [2026-04-14] - Phase 20 Pipeline UX Improvements (V7.1)
- **Milestone**: Rolled out the 4 major UX improvements to drastically enhance production-grade usability.
- **Status**: Stable.
- **Features**:
    - **Batch Reprocess UI**: Replaced the "Yes/No" or silent skip mechanisms with an interactive numbered list selector. Users can dynamically choose which completed files to reprocess without altering code.
    - **Stable Ordering**: `get_tasks()` now intrinsically sorts operations by `(Subject, Filename)`, resolving filesystem IO randomness across Mac/Linux platforms.
    - **Graceful Interruptions (Pause/Stop)**: Trapping `SIGINT` (Ctrl+C) now offers a UI prompt to gracefully `Pause` and save progress to the state manager, or completely `Stop`. Hardware constraints (like RAM thresholds) automatically invoke the Pause sequence.
        - **Apple Unified Memory Hotfix**: Recalibrated macOS hardware defense RAM thresholds (Warning: 500MB, Critical: 200MB) to securely accommodate `qwen3:14b` (~10GB) while maintaining a safe kernel panic buffer.
        - **Thread Zombie Fix**: Audited background `tqdm` polling instances and discovered/fixed a hidden deadlock in `notion_synthesis.py` Phase 5 where throwing exceptions during `Agentic Mermaid` autorecovery loops bypassed the `stop_tick` daemon event by cleanly enforcing Python `finally` structures.
    - **Checkpoint Resume**: Integrated into `run_all.py`. On startup, it detects checkpoints inside `.pipeline_state.json`, prompting the user to resume an abandoned workload. Overridden optionally via the `--resume` flag.

## [2026-04-12] - V7.1 Top-Tier AI Synchronization & Local Git Automation
- **Milestone**: Established the "7th Dimension" coding guidelines. All AI operators now autonomously sync 6 state MD files and execute local `git commit` sequences.
- **Status**: Stable.
- **Features**: 
    - `Coding Guidelines`: Embedded strict AI interaction protocols (Testing first, Auto Commit).
    - `Git Rollback Layer`: The architecture natively leverages local `git` checkpoints without requiring a Github origin.
## [2026-04-12] - V7.0 Object-Oriented Framework & DAG Cascade Invalidation
- **Milestone**: Total architecture refactor completely replacing procedural scripts with modular OOP base classes (`core/`), enforcing strict DAG hash-tracking for incremental compilation, and implementing Agentic self-healing mechanisms.
- **Status**: Stable.
- **Features**:
    - `core/pipeline_base.py` — NEW: Abstract base class standardising tqdm progress bars, system health metrics, gracefully handling interrupts (`SIGINT`), and loading prompts.
    - `core/state_manager.py` — NEW: Implements true DAG state with `.pipeline_state.json`. Replaces dumb checkboxes with intelligent SHA-256 cascade invalidation; manually editing a file now automatically resets dependent downstream phases to `⏳` without needing `--force`.
    - `core/llm_client.py` — NEW: Dedicated API wrapper for Ollama with built-in retries, graceful handling of connection pools, and automatic `keep_alive: 0` VRAM teardowns.
    - Script Optimization — All `_tool.py` files reduced from ~250 lines to ~80 lines. Purely focused on their proprietary prompt schemas and structural logic. 
    - `notion_synthesis.py` (Phase 5) — Enriched with **Agentic Retry Mermaid validation**. If LLM outputs broken mermaid graphs without `mindmap` headers, the script detects the flaw and autonomously feeds the error back to the LLM to heal the syntax output.
    - `run_all.py` — Completely rewritten. Automatically renders read-only `checklist.md` dashboards.
    - YAML Metadata Headers — Added natively to Notion output files for strict version tracking logic (timestamps, chars, pipeline version).

## [2026-04-09] - Phase 0 Glossary Auto-Generation & Full Pipeline Quality Hardening (V5.2)
- **Milestone**: Added automated Whisper ASR misrecognition detection (Phase 0) and completed all remaining code quality improvements from the full pipeline review.
- **Status**: Stable.
- **Features**:
    - `glossary_tool.py` (Phase 0) — NEW: analyses `01_transcript/<subject>/` samples via LLM to auto-detect Whisper misrecognitions and writes draft `raw_data/<subject>/glossary.json`. Supports `--merge` (append-only) and `--force` (overwrite) modes. Output is a draft requiring human review before Phase 2.
    - `prompt.md` Phase 0 — NEW: ASR error analyst role with strict JSON-only output, phonetic+semantic misrecognition criteria, and quality filters.
    - `config.json` phase0 profile — NEW: `gemma3:12b` default, `qwen2.5:14b` recommended alternative.
    - `run_all.py` — Extended: `--glossary`, `--glossary-merge`, `--glossary-force` flags; `--from 99` to skip all phases (glossary-only mode); interactive pause after Phase 0 in `--interactive` mode.
    - `notion_synthesis.py` (Phase 5) — Fixed: strips `## 📋 Phase 3 修改日誌` and `==highlight==` markers from input before LLM synthesis (markers not semantically useful for note generation).
    - `subject_manager.call_ollama()` — Fixed: empty-response guard; raises `ValueError` if Ollama returns empty/whitespace string (caused by num_predict exhaustion or partial timeout).
    - `subject_manager.update_task_status()` — 擴充：新增 `char_count` 可選參數，記錄各 Phase 輸出字元數到 checklist（用於跨 Phase 長度變化追蹤）。
    - `proofread_tool.py` / `merge_tool.py` — 接入 `char_count`：Phase 2/3 完成後，自動記錄輸出字元數到 checklist。
    - `diff_tool.py` (Phase 2.5) — NEW: 生成 HTML 並排差異報告（`01_transcript/` vs `02_proofread/`），暗色主題，無外部依賴，輸出 `.diff.html` 到 `02_proofread/<subject>/`。支援 `--open` 自動開啟瀏覽器。
    - `audit_tool.py` — NEW: 跨 Phase 修改日誌彙整工具，從 Phase 2/3 所有 `.md` 日誌提取 `原文→修正後` 條目，去重計頻，輸出 `02_proofread/<subject>/校對總報告.md`。支援 `--min-count` 篩選高頻條目。
    - `prompt.md` — Version bump from V5.1 → V5.2.

## [2026-04-09] - Glossary Injection, Audit Log & Bug Fixes (V5.1)

- **Milestone**: Implemented per-subject glossary injection, structured cross-phase audit logs, and fixed three output quality bugs.
- **Status**: Stable.
- **Features**:
    - `subject_manager.get_glossary(subject)` — reads `raw_data/<subject>/glossary.json`, formats as `【術語詞庫】` LLM prompt block; silent no-op if file absent.
    - `proofread_tool.py` (Phase 2) rewritten with: glossary injection; **Lookback Context Window** (200 chars of previous chunk as non-output hint); **Verbatim Guard** (fallback to original if output < 85% of input); change log deduplication (strips repeated headers + identical entries from LLM loops).
    - `merge_tool.py` (Phase 3) enhanced with: glossary injection; `術語與數據校準` Section B (oral filler denoising, numerical consistency, subject recovery); Phase 3 audit log written to output file.
    - `prompt.md` Phase 2 — Rules #6 (Data Integrity: PDF overrides audio approximation) and #7 (Glossary Priority). Log format: one header, before≠after required.
    - `prompt.md` Phase 3 — Section B with explicit filler token list; Phase 3 log format requirement.
    - `transcribe_tool.py` — **Bug fix**: non-timestamped transcript was a single wall-of-text line; now one line per Whisper segment. Fix applied to both engine paths.
    - **Origin of `state/` folder confirmed**: created by Open Claw agent framework, not by any pipeline script.

## [2026-04-07] - Five-Phase Pipeline Refactor — Separation of Concerns (V5.0)
- **Milestone**: Complete architectural redesign from 3-phase to 5-phase pipeline with strict I/O separation.
- **Status**: Stable.
- **Features**:
    - Output directories renamed with numeric prefixes (`01_transcript/`, `02_proofread/`, `03_merged/`, `04_highlighted/`, `05_notion_synthesis/`) for explicit data lineage and correct sort order.
    - `proofread_tool.py` (Phase 2): Stripped of all merge logic — now a pure 1:1 segment corrector. Verbatim Integrity is the sole concern.
    - `merge_tool.py` (Phase 3) **NEW**: Handles segment grouping, edit-log stripping, paragraph breaking, and multi-speaker diarization. Special `助人歷程` subject handling with `助人者 (同學A)：` / `個案 (同學B)：` role labels.
    - `highlight_tool.py` (Phase 4) **NEW**: Non-destructive Markdown emphasis pass. Anti-tampering guard: if LLM output is >5% shorter than input, original chunk is used as fallback.
    - `notion_synthesis.py` (Phase 5): Now reads from `04_highlighted/`; checklist tracking key updated to `p5`.
    - `run_all.py` **NEW**: 5-phase orchestrator supporting `--interactive`, `--from N`, and `--force` flags.
    - `subject_manager.py`: Added `MERGED_DIR`, `HIGHLIGHTED_DIR`; 5-column checklist (P1–P5); legacy 3-column data auto-migrated with `⏳` padding on first read.
    - `config.json`: Extended with `phase3`, `phase4`, `phase5` profiles.
    - `prompt.md`: Added Phase 3 (speaker diarization), Phase 4 (anti-tampering highlight), Phase 5 (Notion synthesis) sections.

## [2026-04-03] - File Progress Counter & Phase 2 Segment Merging (V4.4)
- **Milestone**: Added `[X/Y]` file progress counters across all phases and automated multi-segment lecture merging in Phase 2.
- **Status**: Stable.
- **Features**:
    - All three Phase scripts now pre-filter pending tasks before the loop, displaying a total count summary and `[X/Y]` prefix on each file's log line.
    - `proofread_tool.py` gained three new functions: `get_lecture_base()` (regex segment parser), `group_tasks_by_lecture()` (task grouper), and `merge_proofread_segments()` (merger).
    - Segmented lectures (e.g., `L01-1.m4a`, `L01-2.m4a`) are automatically detected, individually proofread, then merged into `L01_merged.md` with a combined modification log.
    - Shared PDF fallback: if `L01-1.pdf` is absent, `L01.pdf` is auto-matched as the reference document for all segments.

## [2026-04-02] - Host Environment Hardening & Storage Isolation (V4.3)
- **Milestone**: Achieved full sandbox isolation of externally pulled HuggingFace payloads ensuring a sterile root macOS environment.
- **Status**: Stable.
- **Features**: 
    - Eliminated legacy Docker volume footprints (`download_root="/models"`) resulting in Read-Only System errors on macOS.
    - Successfully spoofed HuggingFace environment variables (`HF_HOME`, `HF_HUB_CACHE`) at script start to capture and trap multi-model weights caching strictly inside `open-claw-workspace/models/`.
    - Maintained configuration flexibility by officially reverting `config.json` back to standard `faster-whisper` and purging heavy experimental components (`mlx-community` weights) seamlessly via CLI.
    - Eradicated legacy Docker DNS resolvers (`host.docker.internal`) in favor of direct Localhost bridging (`127.0.0.1`) for uninterrupted native Ollama REST API connectivity.

## [2026-04-02] - Progress UI Upgrade (V4.2)
- **Milestone**: Implemented precise, non-blocking progress bars and ETA estimations for the transcription and proofreading pipelines.
- **Status**: Stable.
- **Features**: 
    - Introduced `tqdm` integrations across Phase 1 and Phase 2 loops.
    - Updated `subject_manager.py`'s centralized logging to `tqdm.write()` to seamlessly interleave system logs safely without breaking the progress UI.
    - Engineered an asynchronous UI multi-threading architecture (`threading.Event`) to overwrite the `mlx-whisper` `verbose=True` workaround. This provides a clean, continuously updating elapsed-time progress bar across all synchronous pipeline operations (including Phase 2 and Phase 3 Ollama blocks) without flooding standard output.

## [2026-04-02] - MLX-Whisper & MPS Architecture Optimization (V4.1)
- **Milestone**: Outgrew Docker Sandbox overhead by introducing pure Apple Silicon native operations.
- **Status**: Stable.
- **Features**: 
    - Migrated structural transcription engine dependencies in Phase 1 enabling dynamic `engine` swaps (between `faster-whisper` and `mlx-whisper`).
    - Successfully validated Native MacOS Execution boundaries under Open-Claw logic.
    - Added Active LLM Teardown (`keep_alive: 0`) post-processing to explicitly reclaim deep VRAM logic hooks, preventing terminal paralysis caused by Ollama holdbacks.
    - Corrected false-positive death spirals created by Unified Memory overlapping between native mac host environment processes and our system self-defense monitor thresholds.

## [2026-04-02] - Open Claw Skill Deployment (V4.0.1)
- **Milestone**: The Python pipeline is officially formulated as an Open Claw actionable skill.
- **Status**: Stable.
- **Features**: 
    - Migrated script execution into `skills/voice-memo/scripts/`.
    - Added `SKILL.md` payload for the Telegram Agent, enabling conversational scheduling and processing of the pipeline.
    - Updated Agent CLI capabilities to natively leverage macOS (`python3` rather than `python`) to fix silent command failures during prompt mapping.

## [2026-04-02] - UX Dynamic Path Mapping (V3.6.1)
- **Milestone**: Dynamically generated terminal paths relative to actual phase folders.
- **Status**: Stable.
- **Features**: 
    - `ask_reprocess` now correctly constructs and prints `notion_synthesis/subject/filename.md` instead of hardcoding raw `.m4a` filenames in prompts.

## [2026-04-02] - Context Window Extinction Fix (V3.6)
- **Milestone**: Overcame hardware token eviction limits on massive AI transcripts.
- **Status**: Stable.
- **Features**: 
    - Pinned Phase 3 `num_ctx` to 16,384 in `config.json` to prevent Ollama from silently evicting payload format specifications.
    - Locked `temperature: 0.2` for absolute format compliance.

## [2026-04-02] - Descriptive Hierarchy Flattening (V3.5.2)
- **Milestone**: Rerolled Phase 8 into a purely descriptive, flat list logic scheme instead of hardcore templating.
- **Status**: Stable.
- **Features**: 
    - Extracted all formatting tiers into top-level rules (1-7) to fix LLM skipping nested lists.
    - Attached uppercase `(DO NOT SKIP)` labels to Feynman and Cornell blocks.

## [2026-04-02] - Prompt Parser Fix (V3.5.1)
- **Milestone**: Protected complex markdown structures inside `.md` prompts from naive string collision.
- **Status**: Stable.
- **Features**: 
    - Rewrote the `get_prompt_from_md` parsing engine to strictly recognize `## Phase ` boundaries, freeing up inner heading syntax.

## [2026-04-02] - Prompt Injection Fix (V3.4)
- **Milestone**: Re-engineered prompt injection logic in Phase 3.
- **Status**: Stable.
- **Features**: 
    - Introduced `{INPUT_CONTENT}` dynamic placeholder to embed long transcripts.
    - Mitigated "Lost-in-the-middle" LLM forgetting behavior by shifting strict output formatting requirements to the bottom-most boundary.

## [2026-04-02] - Prompt Encapsulation (V3.3)
- **Milestone**: Full decoupling of prompt rules from Python scripts.
- **Status**: Stable.
- **Features**: 
    - Moved the strict format guards out of `notion_synthesis.py` and into the external `prompt.md`.

## [2026-04-02] - Synthesis Pipeline Hotfix (V3.2)
- **Milestone**: Isolated Context Windows between Phase 2 and Phase 3 to fix LLM conversational hallucination.
- **Status**: Stable.
- **Features**: 
    - Extracted and skipped "Editing Logs Context" from Phase 2 files entering Phase 3.
    - Attached systemic strict-format defense payload on top of Ollama prompts.

## [2026-04-02] - Structural Renaming & Dual-Track Transcripts (V3.1)
- **Milestone**: Refactored the core directory logic to be semantic (`raw_data`, `transcript`...) and introduced `_timestamped.md` outputs.
- **Status**: Stable.
- **Features**: 
    - Renamed confusing directories.
    - Updated `prompt.md` to a Universal Edition, stripping hardcoded terminology.
    - Phase 1 now generates both continuous prose and MM:SS timestamped transcriptions simultaneously.

## [2026-04-02] - Production Grade Upgrade (V3.0)
- **Milestone**: Refactored configurations, unified checklists, and strengthened error handling.
- **Status**: Stable.
- **Features**: 
    - Migrated configurations to JSON `config.json` enabling multiple active Model Profiles.
    - Centralized `checklist.md` globally for all subjects to prevent directory pollution.
    - Fortified `call_ollama` API with Timeout settings and robust Retry logic.
    - Unified the interaction (`should_process_task`) avoiding hardcoding of Phase behaviors.

## [2026-04-01] - Stable Release V2.5
- **Milestone**: Implementation of the "Governed Pipeline".
- **Status**: Stable.
- **Features**: 
    - Multi-Phase workflow (P1/P2/P3).
    - Governed thermal and battery safety.
    - 1:1 PDF-to-Audio matching for academic context.

## Current Build Metrics
- **Model Configuration**: Dynamic (Defined in `config.json`).
- **Logic**: Centralized state management with SHA-256 Hashing for deduplication.