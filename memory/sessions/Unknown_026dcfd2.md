# [Archived] Pipeline UX 四大改進實作計畫

> **Date:** Unknown
> **Session ID:** `026dcfd2`

---

## 1. Implementation Plan

# Pipeline UX 四大改進實作計畫

## 背景

當前 Pipeline 存在四個影響使用者體驗的核心問題，本計畫逐一分析根因並提出生產級解法。

---

## 問題分析 & 解決方案

### 🐛 問題 1：`--subject` 無效，直接跳過

**根因**：`PipelineBase.get_tasks()` (line 189) 在非 `force` 模式下，如果任何 phase 狀態已是 `✅` 就直接 `continue` 跳過，與 `subject_filter` 無關。但更根本的問題在於 `run_all.py` 的 `Phase1Transcribe().run()` 若 `force=False`，Phase 1 所有已轉錄的檔案都不會進入 pending 列表，導致後續 Phase 也無從觸發。

**核心誤區**：`--subject` 的語意應是「只處理這個科目」，但目前的過濾邏輯是「只有未完成的任務才進列表」。若整個科目都已完成，列表為空，`--subject` 就形同無效。

**修正**：此問題本身是正確行為——`--subject` 搭配 `--force` 才能強制重跑。問題是**沒有清楚告知使用者**。但 **更大的問題是問題 2**（重複文件的互動方式）發生在 `get_tasks()` 之後，若問題 2 修正為批量選擇，那麼 `--subject` 的跳過行為就變得合理。

**因此問題 1 的修正方向**：在 Phase 開始時列印「有 N 個已完成的檔案被跳過」的清楚提示，讓使用者知道要用 `--force` 或問題 2 的批量選擇介面。

---

### 🐛 問題 2：重複文件需逐一 yes/no，無法批量選擇

**根因**：`should_process_task()` (subject_manager.py line 276~291) 和 `PipelineBase.get_tasks()` (pipeline_base.py line 177~192) 在收集任務時，**對每個已完成的文件逐一呼叫 `ask_reprocess()`**，造成每個檔案都要個別回答。

**解決方案**：在 `PipelineBase.get_tasks()` 中，先收集所有「已完成」的任務，然後一次性顯示互動式清單 UI，讓使用者勾選哪些要重跑，並提供 `[A] All`、`[S] Skip All` 選項。

**UI 設計**（純 Terminal，無外部依賴）：
```
╔══════════════════════════════════════════════╗
║   偵測到 5 個已完成的 P1 任務，請選擇處理方式：       ║
╚══════════════════════════════════════════════╝
  [1] ○ 生理心理學 / lecture_01.m4a
  [2] ○ 生理心理學 / lecture_02.m4a
  [3] ○ 社會心理學 / lecture_01.m4a
  ...

  輸入指令：
    數字 (1,3,5) → 切換選取
    A             → 全選重新處理
    S             → 全部跳過 (預設)
    Enter         → 確認
```

---

### 🐛 問題 3：處理文件未依照檔案名稱排序

**根因**：`StateManager.sync_physical_files()` 使用 `os.listdir()` / `glob.glob()` 掃描，回傳順序是檔案系統的原生順序（非字母序）。`PipelineBase.get_tasks()` 疊代 `self.state_manager.state.items()` 也沒有排序。

**修正**：在 `PipelineBase.get_tasks()` 的 pending list 組裝完成後，加上 `pending.sort(key=lambda t: (t["subject"], t["filename"]))` 確保跨平台的一致排序。

---

### 🐛 問題 4：中斷後無法暫停/繼續，只能重新開始

**根因**：當前只有「優雅停機」(設定 `stop_requested = True` 後等當前檔案完成) 和「強制停機」(`os._exit(1)`) 兩態。沒有「暫停」機制。

**解決方案**：實作 **SIGTSTP / 暫停-繼續機制** + **斷點續傳 (Resume Checkpoint)**：

1. **SIGTSTP 暫停**：捕捉 `SIGTSTP` 訊號（`Ctrl+Z`），暫停當前任務（等現有 API 呼叫完成），保存當前位置到 `.pipeline_state.json`，然後等待 SIGCONT。

2. **Resume Checkpoint**：在 `.pipeline_state.json` 新增 `"checkpoint"` 欄位，記錄「最後一次被暫停的科目/檔案/Phase」。Resume 時從 checkpoint 繼續。

3. **MAC 特殊處理**：macOS 支援 SIGTSTP，可直接使用。另外，也支援 `Ctrl+C` 後詢問「是否暫停 (P) 或停止 (S)？」的互動問答方式，更友善。

**實作策略**：使用更簡單的「Ctrl+C 後問 Pause/Stop」方式，不依賴 SIGTSTP（跨終端更兼容）：

```
🛑 收到中斷指令！請選擇：
  [P] 暫停 - 保存進度，稍後從此繼續
  [S] 停止 - 清空 Checkpoint，完整停止
  輸入 (p/s):
```

暫停後在 state file 存一個 `checkpoint`，下次跑 `run_all.py` 時如果有 checkpoint，自動詢問是否從上次繼續。

---

## Proposed Changes

### Component 1: `core/pipeline_base.py`

#### [MODIFY] [pipeline_base.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/core/pipeline_base.py)

**改動項目**：
1. `_setup_signals()` — 改為 Ctrl+C 後詢問 Pause/Stop
2. `get_tasks()` — 加入檔案名排序 + 全新的批量重跑選擇器 + 記錄已跳過數量
3. 新增 `_batch_select_reprocess()` — 帶互動式清單 UI 的批量選擇器
4. 新增 `save_checkpoint()` / `load_checkpoint()` / `clear_checkpoint()` — 斷點管理

---

### Component 2: `core/state_manager.py`

#### [MODIFY] [state_manager.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/core/state_manager.py)

**改動項目**：
1. 新增 `save_checkpoint()` — 保存 `{subject, filename, phase, phase_idx}` 到 `.pipeline_state.json`
2. 新增 `load_checkpoint()` — 讀取 checkpoint
3. 新增 `clear_checkpoint()` — 清除 checkpoint

---

### Component 3: `run_all.py`

#### [MODIFY] [run_all.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/run_all.py)

**改動項目**：
1. 啟動時偵測 checkpoint，詢問是否 resume
2. `--resume` flag 強制從 checkpoint 繼續

---

### 不需修改的文件

- `transcribe_tool.py`, `proofread_tool.py`, `merge_tool.py`, `highlight_tool.py`, `notion_synthesis.py`：所有 Phase 腳本的 `run()` 方法不需改動，UX 改進完全封裝在 `PipelineBase.get_tasks()` 內。
- `subject_manager.py`：舊版輔助函式，`ask_reprocess()` 和 `should_process_task()` 已被 `PipelineBase` 架構取代，不需改動。

---

## 技術細節

### 批量選擇器 UI 衝突處理

> [!IMPORTANT]
> `tqdm` progress bar 與 `input()` 互動式 UI 衝突。批量選擇器必須在 tqdm context 外呼叫（get_tasks 階段），且選擇完成後才進入各 phase 的 tqdm 進度條階段。這天然上是正確的——收集任務 → 使用者確認 → 開始處理。

### 暫停/繼續的原子性

> [!WARNING]
> Checkpoint 必須記錄到 state file，而不是記憶體中，否則若程序 crash（非 Ctrl+C），checkpoint 會遺失。每次任務完成後才更新 checkpoint 到下一個任務，確保 checkpoint 永遠指向「下一個待處理的起點」。

### SIGINT 與 input() 衝突

在等待使用者輸入 (Pause/Stop?) 期間，再次按 Ctrl+C 會觸發第二次 SIGINT。需用 try/except KeyboardInterrupt 處理，直接視為「強制停止」。

---

## 驗證計畫

### 問題 1 驗證
```bash
# 預期：清楚顯示「N 個檔案已完成被跳過，使用 --force 強制重跑」
python run_all.py --subject 生理心理學
```

### 問題 2 驗證
```bash
# 預期：顯示批量選擇清單
python run_all.py --subject 生理心理學 --from 2
```

### 問題 3 驗證
```bash
# 驗證終端機輸出的任務順序是否按 lecture_01.m4a, lecture_02.m4a... 排列
python run_all.py --subject 生理心理學 --from 2 --force
```

### 問題 4 驗證
```bash
# Step 1: 開始跑，Ctrl+C 後選 P (暫停)
python run_all.py --subject 生理心理學

# Step 2: 驗證 .pipeline_state.json 有 checkpoint 欄位
cat voice-memo/.pipeline_state.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('_checkpoint', '無 checkpoint'))"

# Step 3: 重新跑，預期自動詢問是否從 checkpoint 繼續
python run_all.py --subject 生理心理學
```


---

## 2. Walkthrough / Summary

*(No Walkthrough)*

---

## 3. Tasks Executed

# Pipeline UX 四大改進 - 任務追蹤

- `[x]` **core/state_manager.py** — 新增 checkpoint 管理 (save/load/clear)
- `[x]` **core/pipeline_base.py** — 四大改進核心：
  - `[x]` 信號處理：Ctrl+C 詢問 Pause/Stop，RAM 警告自動 checkpoint
  - `[x]` `get_tasks()` — 批量選擇 UI（含已完成檔案，排序，skip all / yes for all）
  - `[x]` `_batch_select_reprocess()` — 互動式清單實作
  - `[x]` checkpoint save/load/clear 方法
- `[x]` **run_all.py** — 啟動時偵測 checkpoint，詢問是否 resume；新增 `--resume` flag
- `[x]` **各 Phase 腳本 (`transcribe`, `proofread`, `merge`, `highlight`, `notion_synthesis`)** — `run` 加入 `resume_from` 參數與 pause checkpoint 寫入邏輯
- `[x]` **Git commit** — 實作完成後自動 commit
- `[x]` **WALKTHROUGH.md** — 更新操作指令與 Phase 20 改進日誌

