# WALKTHROUGH.md — Processing Pipeline Flow

> [!TIP]
> 歡迎來到 Voice-Memo 流水線操作守則。這份指南詳述了各 Phase 如何循序轉換音檔，與應有的使用者指令防呆指南。

## 🚀 Usage Commands (操作指令)
- **全部階段一條龍執行**: `python3 scripts/run_all.py`
- **單獨處理特定科目**: `python3 scripts/run_all.py --subject 生理心理學`
  > 已完成的檔案會顯示**批量選擇清單**，可勾選要重跑的項目（數字切換 / `A` 全選 / `S`/Enter 全部跳過）。
- **強制重跑 (無視 Hash)**: 結尾加上 `--force`（跳過選擇清單，全部重跑）。
- **互動式審查模式 (各 Phase 之間暫停)**: 結尾加上 `--interactive`。
- **從斷點繼續執行**: `python3 scripts/run_all.py --resume` 或 `-r`。
- **暫停執行**: 執行中按 `Ctrl+C`，選 `[P] 暫停` 保存進度；選 `[S] 停止` 不儲存。

## 1. Initialization Phase
The `subject_manager` locks the timezone, reads `config.json`, and performs a global directory scan.
- **Action**: `sync_all_checklists()` generates a hash for every `.m4a` file across all subjects.
- **Output**: A centralised `checklist.md` at the root is updated (5 phase columns: P1–P5).

## 2. Resource Verification
Before *any* file is processed, `check_system_health` is invoked.
> [!WARNING]
> - **macOS threshold**: Warning (Pause) < 500 MB, Critical (Stop) < 200 MB available RAM (accommodates 14B models like Qwen3 relying heavily on macOS Swap).
> - **Failure**: Process hard-kills itself via `os._exit(1)` to protect hardware.

## 3. Phase 0 — Glossary Auto-Generation (`glossary_tool.py`)
*Optional but recommended step before Phase 1/2 for new subjects.*
- **Action**: Reads short text samples from existing `01_transcript/<Subject>/*.md` files.
- **Process**: LLM acts as an ASR error analyst, detecting words that sound alike but are semantically incorrect in the subject domain.
- **Output**: Generates a draft `raw_data/<Subject>/glossary.json` of misrecognition→correction pairs.
- **Note**: This is a DRAFT. Users **must** review the file since the LLM may over-flag items. Use `--merge` to add new detections to an existing glossary.

## 4. Phase 1 — High-Precision Transcription (`transcribe_tool.py`)
- Reads `.m4a` files from `raw_data/<Subject>/`.
- Outputs **two** Markdown files per audio into `01_transcript/<Subject>/`:
  - `<name>.md` — pure text (LLM input for Phase 2)
  - `<name>_timestamped.md` — time-coded (human reference)
- Engine selected via `config.json → phase1.active_profile`.

## 5. Phase 2 — Contextual Proofreading (`proofread_tool.py`)
- Reads individual segment files from `01_transcript/<Subject>/`.
- Matches audio base name to co-located PDF lecture slides for context injection.
- Corrects terminology, mis-heard names, and audio artefacts **without** restructuring.
- Writes one corrected `.md` per input file into `02_proofread/<Subject>/` (strict 1-to-1 mapping).
- Appends an edit log section (`## 📋 彙整修改日誌`) at the bottom of each file.

## 6. Phase 3 — Merge & Speaker Diarization (`merge_tool.py`)
- Reads from `02_proofread/<Subject>/`.
- Strips Phase 2 edit logs from each segment before merging.
- Groups segmented lectures (e.g. `L01-1`, `L01-2`) and concatenates them into a single `L01.md`.
- Applies LLM-based paragraph breaking and speaker labelling:
  - Standard: `教授：` / `學生：`
  - `助人歷程` subject: `同學A：` / `同學B：` / `助人者 (同學A)：` / `個案 (同學B)：`
- Outputs merged files to `03_merged/<Subject>/`.

## 7. Phase 4 — Highlight & Emphasis (`highlight_tool.py`)
- Reads from `03_merged/<Subject>/`.
- Applies Markdown emphasis (`**bold**`, `==highlight==`, `*italic*`) to key concepts.
- **Anti-tampering**: If the LLM output is >5 % shorter than the input, the chunk is flagged and the original text is used as fallback (zero content loss guaranteed).
- Outputs to `04_highlighted/<Subject>/`.

## 8. Phase 5 — Notion Synthesis (`notion_synthesis.py`)
- Reads from `04_highlighted/<Subject>/`.
- Transforms highlighted transcripts into structured academic notes:
  - 🎓 3 Key Learning Points
  - 📝 Cornell Format Table
  - 🧠 Mermaid Mind Map
  - 💡 QEC (Question-Evidence-Conclusion)
  - 👶 Feynman Analogy
  - 🏷️ Hashtags
- Outputs to `05_notion_synthesis/<Subject>/`.
- Updates checklist `p5` column to `✅`.

---
## 🤖 Antigravity Execution History (Walkthroughs)

### 🕒 [2026-04-02 01:56] Phase 1 - Voice Memo System Refactoring Summary (py_tools)
Completed the rewriting and optimization of the code under `voice-memo/py_tools`:
1. **Added a unified `models.md` configuration file**: Dedicated to recording LLM model names and parameters for each phase.
2. **Optimized the core manager `subject_manager.py`**: Injected four major foundational functions (`get_model_config`, `call_ollama`, `should_process_task`, `get_target_path`).
3. **Unified the 3 phase scripts**: `transcribe_tool.py`, `proofread_tool.py`, and `notion_synthesis.py` were all refactored to consume the `subject_manager`, replacing hardcoded logic.

### 🕒 [2026-04-02 04:44] Phase 2 - Production-Grade Upgrade Summary
1. **JSON Global File Config (`config.json`)**: Deleted `models.md` and introduced JSON supporting profile variants for agile LLM orchestration.
2. **Industrial Resilience**: Enhanced `call_ollama` with a 10-minute timeout buffer and a 3-retry exception loop.
3. **Checklist Centralization**: Eradicated scatter-shot subject marking methods in favor of a single globally aggregated `voice-memo/checklist.md`.

### 🕒 [2026-04-02] Phase 3 - Universal Prompt Update
Removed highly domain-specific terms (e.g. Fregoli, neuropsychology) from `prompt.md` and corrected a filename typo (`prompts.md` -> `prompt.md`) in `py_tools`, ensuring prompts effectively scale across all subjects robustly.

### 🕒 [2026-04-02] Phase 4 - Structural Renaming & Dual-Track Transcripts
1. **Semantic Directory Reorganization**: Formally renamed directories to `raw_data`, `transcript`, `proofread`, and `notion_synthesis`, completely phasing out misleading legacy names like `audio`.
2. **Phase 1 Dual Output Pipeline**: Adjusted `transcribe_tool.py` to yield a pure text `[name].md` for AI processing alongside a timestamp payload variant `[name]_timestamped.md` for human alignment.
3. **Phase 2 Log Accuracy**: Corrected the prompt message string during proofreading to reference the precise target `.md` rather than implying `.m4a` was being read as proofread text. 

### 🕒 [2026-04-02] Phase 5 - Notion Synthesis Context Bugfix
Repaired a system error where Phase 3 yielded useless conversational output ("Excellent work!"):
1. **Context Pollution Filtering**: Blocked phase 2 edit logs by stripping out header markers in the backend prior to Context Window insertion.
2. **Defensive Prompting**: Added a dynamic `CRITICAL OUTPUT FORMAT REQUIREMENT` directive at runtime prior to Ollama dispatch, effectively locking out conversational hallucination.

### 🕒 [2026-04-02] Phase 6 - Prompt Encapsulation
Fully separated the `CRITICAL OUTPUT FORMAT REQUIREMENT` from the python scripts, migrating it dynamically into `prompt.md`. This cements standard architecture by fully decoupling the payload instructions from Python.

### 🕒 [2026-04-02] Phase 9 - Context Window Extinction Fix
Despite devising the smoothest Markdown specification possible in Phase 8, encountering vast transcript payloads (over 40,000 bytes) still caused the model to collapse into useless paragraph summaries. 
**Root Cause Addressed**: Ollama defaulted to a `2048` token context allocation, triggering silent prompt instruction evictions whenever massive texts pushed previous tokens out of memory boundaries. Format specifications placed at the top were practically deleted from consciousness. 
**Resolution**: Permanently pinned `num_ctx: 16384` and `temperature: 0.2` in `config.json` inside Phase 3, guaranteeing vast vision ranges and rigid algorithmic fidelity.

### 🕒 [2026-04-02] Phase 10 - UX Dynamic Path Mapping
The prior `ask_reprocess` prompter read bare task names (e.g., `lecture_06.m4a`), prompting users confusingly at P3 completion ("detected lecture_06.m4a completed P3"). 
**Resolution**: Inserted dynamic path mapping inside `subject_manager.py` that scales with the running phase automatically, constructing accurate directory and extension combinations (`notion_synthesis/Subject/file.md`).

### 🕒 [2026-04-02] Phase 8 (Reroll) - Descriptive Hierarchy Flattening
Subsequent to Phase 7, the LLM omitted Feynman blocks, Cornell structures, and Key Learning notes, while reducing Mindmaps to 1 word elements holding zero Hashtags. 
**Reflection**: Overly deep list hierarchies (1 -> 4 -> A, B, C) consistently invoke skipping behaviors in smaller dense models (like Gemma 3) during prolonged inferences.
**Correction**: 
1. **Prompt Flattening**: Elevated all structural tiers to top-level numerical lists (1 through 7). 
2. **Skip Prevention Flags**: Embedded capital `(DO NOT SKIP THIS SECTION)` directives into frequently missed blocks.
3. **Component Tuning**: Added distinct specifications for Mermaid Node details alongside appending `#Hashtags` mapping tools.

### 🕒 [2026-04-02] Phase 11 - Open Claw Skill Integration
Converted the Python script suite into a scheduled/orchestrated Open Claw Skill.
1. **Directory Migration**: `py_tools/` -> `skills/voice-memo/scripts/`.
2. **Dynamic Resolution**: Altered `subject_manager.py` to auto-detect its workspace parent based on OS environmental injection, enabling native execution independently of Docker.
3. **Interactive Binding**: Built `SKILL.md` exposing Agent invocation commands. The user can now message their AI on Telegram ("run proofreading") instead of navigating shell commands manually.
4. **Shell Execution Hotfix**: Corrected `python` to `python3` inside `SKILL.md` to prevent macOS `command not found` execution failures when the Agent dispatched shell commands.

### 🕒 [2026-04-02] Phase 12 - Hardware Acceleration Swap (MPS) & OS Stabilization
1. **Engine Integration**: Decoupled Phase 1 from solely relying on `faster-whisper` and implemented `mlx-whisper` as a secondary selectable pipeline inside `transcribe_tool.py`.
2. **Profile Bridging**: Added `"apple_silicon_mps"` to `config.json` with an explicit `"engine": "mlx-whisper"` parameter.
3. **Sandbox Independence validation**: Documented why OS-level Sandbox parameters do not logically conflict with dynamic Python child process execution, effectively obsoleting the necessity of Docker virtualization for pure M-Series GPU inference setups.
4. **VRAM Drain Implementation**: Established a robust `unload_ollama_model` routine issuing standard `keep_alive: 0` pings across API thresholds. Drastically resolves macOS freezing events caused by leftover Ollama cache models.
5. **Host Hardware Perception Tuning**: Substituted arbitrary Docker 2048 MB limits with intelligent `darwin` memory inspection (`1500MB`/`500MB`), solving Mac-specific Unity Memory false-positive death-loops natively.

### 🕒 [2026-04-02] Phase 13 - Asynchronous UI Multi-Threading Evolution
1. **The Issue**: Transitioning to `mlx-whisper` and scaling up `Ollama` parameters resulted in synchronous main-thread blocking. This crashed typical `tqdm` logic, freezing terminals and prompting users to execute Panic Interrupts (Double SIGINT), causing severe semaphore leaks in Python's multiprocessing core.
2. **The Fix**: Engineered completely isolated daemon threads governed by `threading.Event` inside all 3 Phases. These threads execute headless, continuously hitting `pbar.refresh()` every 1.0 seconds. 
3. **Result**: The UI now displays a clean, uninterrupted ticking elapsed-timer `[00:15]` completely bypassing text-spam alternatives like `verbose=True`, preserving CLI aesthetics.

### 🕒 [2026-04-02] Phase 14 - Host Environment Sandboxing & Storage Containment
1. **The Vulnerability**: Executing `pip3 install mlx-whisper` allowed HuggingFace Hub to bypass our project bounds and stealthily dump gigabytes of monolithic model weights directly into the macOS user root `~/.cache/huggingface/`.
2. **The Defense**: Injected overriding `HF_HOME` and `HF_HUB_CACHE` environment variables directly at the script header (`transcribe_tool.py`), successfully hijacking the HuggingFace module and strictly mapping monolithic downloads directly back into the localized `open-claw-workspace/models/` sandbox.
3. **Result**: Attained massive Storage Isolation, enabling 1-click cleanups without polluting typical OS caching boundaries.
4. **Network Resolution Validation**: Switching natively to macOS crashed Ollama Phase 2 & 3 scripts because they attempted to query the Docker-exclusive `host.docker.internal` domain name. Standardizing the network variable to `127.0.0.1` eliminated the mapping disruption unconditionally.
5. **Memory Shield Calibration**: Native local-execution limits clashed with large models like `gemma3:12b`, instantly tripping the `2048MB` Memory Exhaustion safeguard. Reconfigured the defense script with a macOS (`darwin`) conditional, safely dropping the Red Line to `300MB` to exploit Apple's robust Swap Architecture.

### 🕒 [2026-04-03] Phase 15 - File Progress Counter & Phase 2 Segment Merging

**Problem 1 — No Overall Progress Visibility**: Users had no way to know how many files remained during a batch run. The terminal only showed per-file tqdm bars with no aggregate count.

**Resolution**:
1. **Pre-filter Pattern**: All three Phase scripts now call `should_process_task()` upfront to build a `pending_tasks` list before the loop starts, giving an accurate total count.
2. **[X/Y] Counter**: Each script prints a summary (`📋 Phase N 共有 X 個檔案待處理`) before the loop, then prefixes each file's log message with `[idx/total]` — e.g., `🎙️ [1/3] 正在處理：[科目] L01.m4a`.

**Problem 2 — Split Lectures Produce Fragmented Proofread Files**: When a single lecture is recorded in multiple segments (`L01-1.m4a`, `L01-2.m4a`), each segment was proofread and saved as a separate file, making Phase 3 synthesis incomplete.

**Resolution** (new functions in `proofread_tool.py`):
1. **`get_lecture_base(fname)`**: Regex parser — extracts `base="L01"`, `seg=1` from `L01-1.m4a`. Non-segmented files return `seg=None`.
2. **`group_tasks_by_lecture(tasks)`**: Groups tasks by `(subject, lecture_base)` and sorts each group by segment number.
3. **`merge_proofread_segments(subj, base_name, segment_tasks)`**: After all segments of a lecture complete proofreading, concatenates corrected text bodies (with `<!-- 段落：L01-1 -->` dividers), and unifies all modification logs into a single `## 📋 彙整修改日誌（合併版）` section. Output: `proofread/<subj>/L01_merged.md`.
4. **Shared PDF Fallback**: If `L01-1.pdf` is not found, the system automatically searches for `L01.pdf` to use as reference material for all segments.

### 🕒 [2026-04-07] Phase 16 — V5.0 Five-Phase Pipeline Refactor

Complete architectural redesign driven by **Separation of Concerns** principles.

**Motivation**: The original 3-phase design conflated proofreading, merging, and synthesis into too few steps, causing LLM context pollution and accumulating errors across phases.

**Changes Made**:
1. **Directory renaming**: Output folders now carry numeric prefixes (`01_transcript`, `02_proofread`, `03_merged`, `04_highlighted`, `05_notion_synthesis`) for clarity and sort-order.
2. **`proofread_tool.py` (Phase 2)**: Stripped of all merge logic — now purely a 1-to-1 file corrector.
3. **`merge_tool.py` (Phase 3) — NEW**: Handles segment grouping, edit-log stripping, and multi-speaker diarization. Includes special handling for `助人歷程` subject (student practice dialogues with roles `助人者` / `個案`).
4. **`highlight_tool.py` (Phase 4) — NEW**: Non-destructive emphasis pass with anti-tampering word-count guard (>5 % length drop → fallback to original chunk).
5. **`notion_synthesis.py` (Phase 5)**: Now reads from `04_highlighted/` instead of `02_proofread/`; tracking key updated to `p5`.
6. **`run_all.py` — NEW**: Orchestrator supporting `--interactive` (human-in-the-loop pause after each phase), `--from N` (resume from a specific phase), and `--force` (ignore ✅ status).
7. **`prompt.md`**: Added dedicated sections for Phase 3 (speaker diarization logic including `助人歷程` edge cases), Phase 4 (anti-tampering highlight rules), and Phase 5 (renamed from old Phase 3).
8. **`config.json`**: Extended to include `phase3`, `phase4`, and `phase5` profiles.
9. **`subject_manager.py`**: Added `MERGED_DIR`, `HIGHLIGHTED_DIR`; checklist updated to 5 columns (P1–P5); legacy 3-column data auto-migrated with `⏳` padding on first read. Module-level docstring added.
10. **All scripts**: Uniform `# -*- coding: utf-8 -*-` header, module-level docstrings, and inline section comments.

### 🕒 [2026-04-08] Phase 17 — Glossary Injection & Phase 2/3 Prompt Optimisation (V5.1)

**實作詞庫注入與跨 Phase 領域術語精確性強化。**

1. **`subject_manager.get_glossary(subject)`** — 讀取 `raw_data/<subject>/glossary.json`（平坦 `{"misrecognition": "correct_term"}` 格式），輸出為 `【術語詞庫】` prompt 區塊；檔案不存在時回傳 `""` (graceful degradation)。
2. **`proofread_tool.py` (Phase 2)** — 完整重寫 (V5.1)：
   - Glossary loaded once per subject; injected into every chunk's prompt.
   - **Lookback Context Window** (200 chars)：前置上下文注入，防止術語在 chunk 邊界被截斷。
   - **Verbatim Guard**：若 LLM 輸出 < 85% 輸入長度，fallback 至原始 chunk 並記錄 `⚠️` 警告。
   - **Change log deduplication**：去除重複的 `Explanation of Changes` 標頭；去除連續相同條目。
3. **`merge_tool.py` (Phase 3)**：Glossary injected as lightweight reference; `p3_log_items` initialized; Phase 3 change log parsed and deduplicated.
4. **`prompt.md` Phase 2** — Rules #6 (Data Integrity) & #7 (Glossary Priority); strict single-header log format.
5. **`prompt.md` Phase 3** — Section B (術語與數據校準): oral filler denoising, numerical consistency, subject recovery, glossary calibration; Phase 3 log format.

### 🕒 [2026-04-08] Phase 18 — Bug Fixes & Output Quality Hardening

**三個輸出品質 bug 發現並修復（透過 timestamped vs. non-timestamped 比對及 Phase 2 修改日誌分析）。**

1. **`transcribe_tool.py` — 非 Timestamped 單行巨型文字 Bug（已修復）**
   - 原始：`pure_text += text_val` — 所有 Whisper 片段被串接成單一 40KB+ 行，無換行分隔。
   - 影響：chunk 邊界切在英文字中間（如 `action taki` / `ng`）；LLM 無段落結構可參考。
   - 修復：`pure_text += text_val.strip() + "\n"` — 每個 Whisper 片段獨立一行。已套用至 mlx-whisper 及 faster-whisper 兩條路徑。

2. **`proofread_tool.py` — 修改日誌重複迴圈 Bug（已修復）**
   - 現象：`02_proofread/助人歷程/L02-1.md` 의 修改日誌中，LLM 將 `equip → equip`（before = after）寫了 120+ 次；每個 chunk 各自產生一個 `## Explanation of Changes:` 標頭，導致日誌有 9 個標頭。
   - 根本原因：LLM context window 末端重複幻覺 + Python 層沒有去重防護。
   - 修復：Python 層去重守衛 — 跳過已知標頭行（case-insensitive）；跳過與前一行完全相同的條目（`seen_last` 模式）。所有 chunk 的日誌統一匯整後，只寫一個標頭。

3. **`merge_tool.py` — Phase 3 修改日誌 & `p3_log_items`（已修復 + 新增）**
   - 修復 lint 錯誤 `ef68a28a`：`p3_log_items` 在 chunk 迴圈前正確初始化。
   - 新增：Phase 3 解析 LLM 回應中的 `## 📋 Phase 3 修改日誌`，去重後追加至輸出檔案，實現跨 Phase 人工核實追蹤。

4. **`state/` 資料夾來源確認**
   - 確認：`open-claw-workspace/state/` 由 **Open Claw agent framework** 建立（heartbeat state，見 `AGENTS.md`），與 voice-memo pipeline 腳本完全無關。`L02-1.md` 中的「一個 state」是教授講課的英文術語，Whisper 正確聽寫，非程式產物。

### 🕒 [2026-04-09] Phase 19 — Glossary Auto-Gen & Full Pipeline Quality Hardening

1. **`glossary_tool.py` (Phase 0)**
   - **新增**: Automated ASR error detection logic added as an optional precursor to Phase 1/2. Generates draft `glossary.json` files for human review to accelerate the dictionary building process. Includes `--merge` and `--force` controls.
2. **`smart_split()` Chunking (Phases 2, 3, 4)**
   - **優化**: Replaced raw character-index slicing (`[i:i+chunk_size]`) with `smart_split()` in `subject_manager.py`. The algorithm prioritised splitting on `\n` (newlines) to prevent chunk boundaries from occurring inside words or academic terms. Chunk size in Phase 2 raised to 3000.
3. **Phase 3 Guardrails & Context**
   - **新增**: Added a Lookback Context Window (last 150 chars of previous chunk injected as hint) to maintain speaker role continuity across chunks.
   - **新增**: Added Verbatim Guard (`P3_VERBATIM_THRESHOLD = 0.70`). Throws warning if output drops below 70% length, ensuring denoising does not aggressively delete content.
4. **Data Stream Sanitisation (Phases 4 & 5)**
   - **修復**: `highlight_tool.py` was unintentionally highlighting Phase 3 log entries. Now strips `## 📋 Phase 3 修改日誌` before processing and re-attaches it afterwards.
   - **防護**: `notion_synthesis.py` now strips `==highlight==` markers and the Phase 3 log from the input stream. This provides the LLM with a pristine semantic stream for high-quality note synthesis.
5. **LLM Engine Hardening**
   - **防護**: `call_ollama()` now raises a `ValueError` if the LLM returns an empty string (e.g. from context window exhaustion), preventing silent truncation bugs. Added `qwen2.5:14b` and `qwen3:14b` as recommended Chinese alternatives in config.

### 🕒 [2026-04-14] Phase 20 — UX 四大改進 (V7.1)

**問題根因分析與解決方案，全部封裝在 `core/pipeline_base.py`，各 Phase 腳本不需改寫業務邏輯。**

#### 改進 1+2：`--subject` 指定科目後，已完成的檔案不再靜默跳過
- **根因**：`get_tasks()` 在非 `force` 模式下，對所有已完成任務做 `continue`，造成「以為在跑，其實全部跳過」。
- **修正**：已完成任務進入批量選擇 UI `_batch_select_reprocess()`，支援數字切換 / `A` 全選 / `S` 或 Enter 全部跳過，用 `A` 立刻確認。

#### 改進 3：任務依檔案名稱字母順序處理
- **根因**：`glob.glob()` 回傳順序是 inode 原生順序，非字母序。
- **修正**：`get_tasks()` 最終排序 `pending.sort(key=lambda t: (t["subject"], t["filename"]))`。

#### 改進 4：新增暫停/繼續（斷點續傳）機制
- Ctrl+C 後詢問 `[P] 暫停` / `[S] 停止`，選暫停才寫 checkpoint。
- RAM 偏低 / 高溫觸發優雅停機也自動保存 checkpoint。
- 下次執行 `run_all.py` 自動偵測並詢問是否繼續，或用 `--resume` flag 強制繼續。
- Checkpoint 存於 `.pipeline_state.json` 的 `_checkpoint` 欄位。

#### 修改的檔案
| 檔案 | 改動 |
|---|---|
| `core/state_manager.py` | 新增 `save/load/clear_checkpoint` |
| `core/pipeline_base.py` | SIGINT→P/S UI, `get_tasks` 批量選擇+排序, `_batch_select_reprocess`, checkpoint 委托, `pause_requested` |
| `run_all.py` | `check_and_resume()`, `--resume` flag, pause/stop checkpoint 處理 |
| 5 個 Phase 腳本 | `run(resume_from=None)` + pause checkpoint |
