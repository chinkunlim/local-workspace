# TASKS.md — Roadmap & Backlog

> [!NOTE]
> 這個全域看板控制著本系統的待辦清單，任何 AI 代理在承接後續開發前，必須首要審視此看板的 Active Development 區塊。

## Active Development
- [x] Integrate SHA-256 hashing for file tracking.
- [x] Implement thermal throttling and battery protection.
- [x] Externalize AI prompts to `prompt.md`.
- [x] Unify Configurations to JSON (`config.json`).
- [x] Consolidate scatter state files to a Global `checklist.md`.
- [x] Create Robust Ollama Fallback/Retry handlers.
- [x] Refactor from 3-phase to 5-phase pipeline (Separation of Concerns).
- [x] `merge_tool.py` — Phase 3 segment merging + speaker diarization.
- [x] `highlight_tool.py` — Phase 4 non-destructive Markdown emphasis.
- [x] `run_all.py` — 5-phase orchestrator with `--interactive`, `--from N`, `--force`.
- [x] `subject_manager.py` — 5-column checklist, legacy migration, `MERGED_DIR`, `HIGHLIGHTED_DIR`.
- [x] Integrate Top-Tier AI Auto-Git Commit and 6-File Sync Protocol.
- [x] Tune macOS `check_system_health` thresholds securely for Qwen3:14B memory profiles.
- [x] Fix Phase 5 Agentic Mermaid Retry headless threading deadlock bug via `finally` wrappers.

## Backlog (Pending Verification)
- [ ] Test "Double-Tap" Force Close on 10GB+ datasets.
- [ ] Verify Mermaid diagram syntax stability across different lecture topics.
- [ ] Optimize `pypdf` extraction to handle multi-column academic papers.
- [ ] Confirm correct term for `「輔料」` (intended: `「輔療技」`?) — for glossary.json population.
- [ ] Confirm whether `「嗯」` in `助人歷程` should be exempted from oral filler denoising.
- [ ] Phase 3 verbatim guard threshold tuning (`0.70`) — monitor real runs to validate.
- [ ] Phase 4 anti-tampering threshold tuning (`0.95`) — monitor if legitimate outputs trigger false fallbacks.
- [ ] Manual test of `smart_split()` on boundary edge cases (e.g., single paragraph > chunk_size).
- [ ] Evaluate `qwen2.5:14b` vs `gemma3:12b` on real transcript samples before switching `active_profile`.

## Backlog (Planned)
- [ ] `diff_tool.py` (optional Phase 2.5): HTML side-by-side diff of `01_transcript/` vs `02_proofread/` using `difflib.HtmlDiff` for human verification.
- [ ] `audit_tool.py` (optional): cross-phase change log aggregator — reads Phase 2 + Phase 3 logs and produces `校對總報告.md` sorted by term.
- [ ] Add character-count tracking to `update_task_status()` (write `P2:5234c P3:4891c` to `note` column in checklist for length verification).
- [ ] `_preserve_fillers` optional field in `glossary.json` schema for subject-specific filler exemptions.
- [ ] Phase 3 output length guard: if output < 70% of input, flag warning (oral denoising should not delete >30% of text) — ⚠️ already implemented as `P3_VERBATIM_THRESHOLD`.

---
## 🤖 Antigravity Execution History (Tasks)

### 🕒 [2026-04-02 01:54] Phase 1 - Code Unification & Models Extraction
- [x] Create `models.md`.
- [x] Implement new methods in `subject_manager.py` (model config parser, ollama API caller, unified should_process_task logic, file path helpers).
- [x] Refactor `transcribe_tool.py` (Phase 1) to use the new system.
- [x] Refactor `proofread_tool.py` (Phase 2) to use the new system.
- [x] Refactor `notion_synthesis.py` (Phase 3) to use the new system.

### 🕒 [2026-04-02 04:40] Phase 2 - Production Grade Upgrade
- [x] Create `voice-memo/config.json`.
- [x] Remove `py_tools/models.md`.
- [x] Refactor `subject_manager.py` (JSON parser, robust `call_ollama`, unified global `checklist.md`).
- [x] Update `proofread_tool.py` and `notion_synthesis.py` to correctly map `options`.

### 🕒 [2026-04-02] Phase 3 - Universal Prompt Update
- [x] Fix broken file reference `prompts.md` to `prompt.md` in `subject_manager.py`.
- [x] Rewrite `prompt.md` instructions removing domain-specific terminology (e.g., Fregoli) completely.

### 🕒 [2026-04-02] Phase 10 - UX Dynamic Path Mapping
- [x] Fix static `ask_reprocess` terminal prompts referencing `.m4a` audio files inappropriately during Phase 2/3.
- [x] Implement dynamic CLI target mapping in `subject_manager.py` using `os.path.relpath` to accurately reflect `transcript`, `proofread`, or `notion_synthesis` sub-directories and correct `.md` extensions.

### 🕒 [2026-04-02] Phase 4 - Structural Rename & Dual Transcripts
- [x] Rename local physical folders (`audio` -> `raw_data`, `raw_text` -> `transcript`, etc.).
- [x] Refactor path definitions in Python scripts.
- [x] Refactor `transcribe_tool.py` to spit out dual formats (`.md` pure prose and `_timestamped.md` for analysis).
- [x] Fix console print output to show `.md` target format instead of `.m4a` when tracking Proofread tasks.

### 🕒 [2026-04-02] Phase 5 - Notion Synthesis Bugfix
- [x] Strip Phase 2 Edit Logs before passing context to LLM in Phase 3.
- [x] Enforce systemic format restriction in `notion_synthesis.py` via `CRITICAL OUTPUT FORMAT REQUIREMENT`.

### 🕒 [2026-04-02] Phase 6 - Prompt Encapsulation Update
- [x] Remove hardcoded `CRITICAL OUTPUT FORMAT REQUIREMENT` rule from `notion_synthesis.py`.
- [x] Move format restrictions fully inside `prompt.md` so that the Python script stays cleanly decoupled from prompt engineering.

### 🕒 [2026-04-02] Phase 7 - Strict Context Injection Fix
- [x] Identify "Lost in the middle" LLM format hallucination caused by huge transcript sizes.
- [x] Implement the `<transcript>{INPUT_CONTENT}</transcript>` dynamic placeholder pattern in `prompt.md`.
- [x] Refactor `notion_synthesis.py` to inject content precisely BEFORE the `CRITICAL FORMAT REQUIREMENT` block to ensure strict compliance.

### 🕒 [2026-04-02] Phase 8 (Reroll) - Descriptive Hierarchy Flattening
- [x] Diagnose LLM skipping Feynman, Cornell, and Key Learning Points in Phase 7.
- [x] Flatten deeply nested instructions (A/B/C) into top-level numbered lists.
- [x] Inject explicit `(DO NOT SKIP THIS SECTION)` constraints for heavily neglected items.
- [x] Add clear Mermaid mindmap node instructions (to include detailed descriptions) and append Hashtag rules.

### 🕒 [2026-04-02] Phase 11 - Open Claw Skill Integration
- [x] Create directory `skills/voice-memo/scripts`.
- [x] Migrate all Python logic from `py_tools/` to the skill directory.
- [x] Refactor `subject_manager.py` pathing to dynamically resolve to the OS workspace root to run anywhere (Local/Docker).
- [x] Define `SKILL.md` to establish Agent invocation endpoints, enabling Telegram interaction and orchestration.
- [x] Enhance Agent parsing fidelity by explicitly converting all `python` commands to `python3` in `SKILL.md` to guarantee native macOS shell compatibility.

### 🕒 [2026-04-02] Phase 12 - MPS Hardware Acceleration Update
- [x] Adapt `transcribe_tool.py` to natively support dynamic switching between `faster-whisper` and `mlx-whisper`.
- [x] Inject `apple_silicon_mps` into Phase 1 of `config.json`.
- [x] Define explicit boundaries verifying that native macOS `python3` child executions fall completely under Open-Claw's Sandbox OS-level containment.
- [x] Unload Ollama Model `keep_alive: 0` API extension payload across Phase 2 / 3 terminations, curing background RAM exhaustion natively via `subject_manager`.
- [x] Re-tune macOS `subject_manager` host hardware monitoring thresholds down to `1500MB`/`500MB` critical to avoid false-positive script deaths caused by aggressive Apple Unified Memory caching techniques.

### 🕒 [2026-04-02] Phase 13 - Progress UI Upgrade
- [x] Integrate `tqdm` for robust progress and ETA tracking during long-running tasks.
- [x] Upgrade `transcribe_tool.py` to calculate ETA accurately using duration benchmarks for `faster-whisper`.
- [x] Implement a background threading architecture (`threading.Event`) to supersede `verbose=True` log streaming for `mlx-whisper` and Ollama `p2/p3` models. This guarantees an asynchronous, ticking elapsed-time progress bar without clogging standard output during long deterministic blocking operations.
- [x] Enhance `proofread_tool.py` to display granular, chunk-based completion progress.
- [x] Refactor `subject_manager.py` global logging (`log_msg`) using `tqdm.write()` to prevent terminal spam/breaking the progress bar format.

### 🕒 [2026-04-02] Phase 14 - Host Environment Hardening & Storage Isolation
- [x] Resolve `[Errno 30] Read-only file system` permissions bug caused by hardcoded absolute paths (`/models`) leftover from Docker virtualization.
- [x] Dynamically construct and map `download_root` for `faster-whisper` relative to `sm.WORKSPACE_ROOT`.
- [x] Inject `HF_HOME` and `HF_HUB_CACHE` environment variables into `transcribe_tool.py` to programmatically block HuggingFace from hoarding cached `mlx-whisper` weights globally in `~/.cache/huggingface/`.
- [x] Force all network-delivered Model Neural Network assets to centralize safely inside `open-claw-workspace/models/` for absolute sandboxing.
- [x] Execute complete systemic rollback and CLI uninstallation of `mlx-whisper` and its massive `mlx-community/whisper-large-v3-mlx` weights to reclaim gigabytes of storage space, formally reverting `config.json` to the default `faster-whisper`.
- [x] Refactor Ollama API endpoints globally from legacy Docker tunnels (`host.docker.internal`) to native Loopback addresses (`127.0.0.1`) preventing `NameResolutionError` during native Phase 2/3 execution.

### 🕒 [2026-04-03] Phase 15 - File Progress Counter & Phase 2 Segment Merging
- [x] Refactor `transcribe_tool.py` to pre-filter tasks via `should_process_task()`, build a `pending_tasks` list, and display `📋 Phase 1 共有 N 個音檔待轉錄` + `🎙️ [X/Y]` counters per file.
- [x] Refactor `notion_synthesis.py` to pre-filter tasks via `should_process_task()` and display `📋 Phase 3 共有 N 個檔案待合成` + `📝 [X/Y]` counters per file.
- [x] Fully rewrite `proofread_tool.py` with the following additions:
    - [x] `get_lecture_base(fname)`: Regex parser to detect segment suffix pattern (e.g., `L01-1` → `base=L01, seg=1`).
    - [x] `group_tasks_by_lecture(tasks)`: Groups all tasks by `(subject, lecture_base)` and sorts each group by segment number.
    - [x] `merge_proofread_segments(subj, base_name, segment_tasks)`: Reads all completed segment proofread files, concatenates corrected bodies with `<!-- 段落：X -->` dividers, and unifies modification logs into `L01_merged.md`.
    - [x] Shared PDF fallback: if segment-specific PDF is missing, auto-detect `{lecture_base}.pdf` as shared reference.
    - [x] `[X/Y]` counter added: `📦 [X/Y] 正在校對：[科目] file.md`.

### 🕒 [2026-04-07] Phase 16 — V5.0 Five-Phase Pipeline Refactor
- [x] Rename output directories with numeric prefixes (`01_` through `05_`).
- [x] Strip merge logic from `proofread_tool.py` (Phase 2 = pure 1:1 corrector).
- [x] Create `merge_tool.py` (Phase 3): segment grouping, edit-log stripping, paragraph formatting, speaker diarization (`助人歷程` special handling).
- [x] Create `highlight_tool.py` (Phase 4): non-destructive Markdown emphasis with anti-tampering word-count guard.
- [x] Rewrite `notion_synthesis.py` as Phase 5: reads `04_highlighted/`, tracks `p5` checklist key.
- [x] Create `run_all.py`: 5-phase orchestrator with `--interactive`, `--from N`, `--force` flags.
- [x] Extend `prompt.md` with Phase 3, Phase 4, Phase 5 sections.
- [x] Extend `config.json` with `phase3`, `phase4`, `phase5` profiles.
- [x] Update `subject_manager.py`: `MERGED_DIR`, `HIGHLIGHTED_DIR`, 5-column checklist, legacy 3-column migration.
- [x] Update `CLAUDE.md` to V5.0 spec; append Phase 16 entry to `WALKTHROUGH.md`.

### 🕒 [2026-04-08] Phase 17 — Glossary Injection & Phase 2/3 Prompt Optimisation (V5.1)
- [x] `subject_manager.get_glossary(subject)` — reads `raw_data/<subject>/glossary.json`; formats as `【術語詞庫】` prompt block; returns `""` if absent (graceful degradation).
- [x] `proofread_tool.py` — fully rewritten (V5.1):
  - [x] Glossary loaded once per subject and injected into every chunk's prompt.
  - [x] Lookback context window (200 chars of previous chunk) injected as non-output hint to prevent boundary terminology errors.
  - [x] Verbatim Guard: if LLM output < 85% of input length, fallback to original chunk with `⚠️` warning.
  - [x] Change log deduplication: repeated `Explanation of Changes` headers and identical log entries stripped before writing.
- [x] `merge_tool.py` — glossary injected into Phase 3 prompt; Phase 3 change log parsed, deduplicated, and appended to output.
- [x] `prompt.md` Phase 2 — added Rule #6 (Data Integrity: PDF value overrides audio approximation) and Rule #7 (Glossary Priority); strict single-header log format specified.
- [x] `prompt.md` Phase 3 — added Section B (術語與數據校準): oral filler denoising (explicit token list), numerical consistency, subject recovery, glossary calibration; Phase 3 log format specified.

### 🕒 [2026-04-08] Phase 18 — Bug Fixes & Output Quality Hardening
- [x] `transcribe_tool.py` — fixed: pure transcript was written as a single wall-of-text line. Now each Whisper segment is written on its own line (`text_val.strip() + "\n"`). Fix applied to both `mlx-whisper` and `faster-whisper` paths.
- [x] `proofread_tool.py` — fixed: change log repetition loop (LLM was writing `equip → equip` 150+ times). Deduplication guard strips same-line repeats and normalises multiple `Explanation of Changes` headers across chunks to exactly one.
- [x] `merge_tool.py` — fixed: `p3_log_items` variable initialised before chunk loop; Phase 3 change log correctly appended to output file.
- [x] Confirmed `open-claw-workspace/state/` folder origin: created by Open Claw agent framework (heartbeat state), not by any voice-memo pipeline script.

### 🕒 [2026-04-09] Phase 19 — Full Pipeline Review & Code Quality Hardening
- [x] **MD 文件一致性審查**：修正 CLAUDE.md pipeline ASCII 圖（加入 `glossary.json`、audit log 標注、Phase 4 log stripping 說明）。
- [x] **`subject_manager.py`**：新增 `smart_split(text, chunk_size)` — 優先在換行符切割 chunk，防止在詞語/學術術語中間截斷。
- [x] **`proofread_tool.py` (Phase 2)**：改用 `sm.smart_split()` 取代 raw character slice；chunk_size 從 2000 升至 3000。
- [x] **`merge_tool.py` (Phase 3)**：改用 `sm.smart_split()`；加入 Lookback Context Window（150 chars，維持 chunk 邊界話者識別連貫性）；加入 Verbatim Guard（閾值 0.70，比 Phase 2 的 0.85 寬鬆）。
- [x] **`highlight_tool.py` (Phase 4)**：修正 Phase 3 audit log 被 LLM highlight 的 bug — 在處理前剝離 `## 📋 Phase 3 修改日誌` 區塊，highlight 後重新附加。
- [x] **`config.json`**：加入 Qwen2.5:14b 和 Qwen3:14b 替代 profile（Phase 2/3/4/5）；加入 Whisper large-v3 profile（Phase 1）；新增 `_note` 說明欄位；Phase 2 chunk_size 從 2000 → 3000。
### 🕒 [2026-04-12] Phase 20 - V7.0 Deep Architecture Upgrade (OOP & DAG)
- [x] Create native Python object-oriented baseline `core/pipeline_base.py`.
- [x] Integrate `core/state_manager.py` with `.pipeline_state.json` as the unified source of truth, establishing DAG Hash tracking for automatic downstream invalidations.
- [x] Wrap `core/llm_client.py` API parameters providing fail-safes without spamming CLI.
- [x] Restructure scripts `transcribe_tool.py`, `proofread_tool.py`, `merge_tool.py`, `highlight_tool.py`, `notion_synthesis.py` leveraging OOP inheritances and eradicating heavy boilerplate operations.
- [x] Add Agentic Retry validation intercept to `Phase 5` specifically for fixing faulty syntax produced by LLM generated Mermaid mindmaps.
- [x] Replace procedural logic within `run_all.py` Orchestrator with structured phase classes and an intelligent CLI state Dashboard.
- [x] Pre-flight Check and YAML Markdown headers implemented.

### 🕒 [2026-04-14] Phase 20 - UX 四大改進 (V7.1)
- [x] Integrate interactive batch selection UI for reprocessing completed tasks.
- [x] Sort tasks alphabetically by (subject, filename) across all phases.
- [x] Implement graceful Pause/Stop signal handling (Ctrl+C).
- [x] Implement Checkpoint/Resume mechanism tracking the `next_task` in `.pipeline_state.json`.
- [x] Add `--resume` flag to Orchestrator to bypass prompts.
- [x] Cascade `resume_from` parameters through `PipelineBase.get_tasks()` to all 5 phase tools.

### 🕒 [2026-04-15] Phase 21 - Dual-Skill Alignment & Extraction (V7.2)
- [x] Integrate global `requirements.txt` and `bootstrap.sh` for universal environment setup spanning both `voice-memo` and `pdf-knowledge`.
- [x] Extract `smart_split()` from Phase 5 into `core/text_utils.py` for shared Map-Reduce scaling.
- [x] Harmonize `CODING_GUIDELINES.md` to formally adopt externalized components (`Resume Manager`) while preserving domain autonomy.
