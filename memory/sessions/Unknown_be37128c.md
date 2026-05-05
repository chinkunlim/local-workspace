# [Archived] 5-Phase Pipeline Architecture Enhancement Plan

> **Date:** Unknown
> **Session ID:** `be37128c`

---

## 1. Implementation Plan

# 5-Phase Pipeline Architecture Enhancement Plan

這份計畫回應並分析你提出的 5 階段自動化錄音轉筆記架構，同時解答關於邏輯可行性及未來優化的問題。

## 邏輯評估與回饋 (Is this logic OK?)

**這是一個極佳且非常專業的架構設計。** 你的核心理念「以精確度為主要考量，避免錯誤累積」在 AI 系統工程中稱為 **Separation of Concerns (關注點分離)**。
過去將「糾錯」、「合併」、「排版」全塞給 Phase 2 容易導致 LLM 發生「顧此失彼」的幻覺。拆解後的優勢非常明顯：

1. **Phase 2 (純校對)**：LLM 只需要死盯著 PDF 和原始逐字稿，專注改錯字，無須分心考慮排版，準確率將大幅提升。
2. **Phase 3 (合併與分段/對話編排)**：先將所有分段合併，LLM 才能擁有「全局上下文 (Global Context)」。有了全局視野，LLM 判斷講者 A (老師)、講者 B (學生) 的準確度才會高，避免在分段獨立處理時發生講者邏輯斷層。
3. **Phase 4 (純重點上色)**：獨立出 Highlight 階段極限保護了「原汁原味的逐字稿」。學術研究極度需要對照原始語境，藉由獨立加上 markdown 星號 `**` 或高亮標籤 `==`，我們能產出一份極具閱讀性的逐字稿，又不會損失任何細節。
4. **Phase 5 (Notion 筆記)**：基於已經是「完美校對、分段精確、且標出重點」的 Phase 4 文本，最後生成的 Notion 筆記品質將會是前所未有的高。

---

## 🔧 系統與細節優化建議 (What else needs to be added/optimized?)

針對「自動化學術錄音轉筆記」，我們還可以加入以下優化：

### 1. 強化 Phase 3 (對話與分段) 的「講者推斷提示 (Speaker Inference)」
學術錄音通常有隱含的身分（例如：教授 vs 提問學生）。在 P3 的 prompt 裡，必須設計獨特的系統級指令，要求 LLM **根據語氣與知識權威度** 自動推斷講者標籤，例如自動將 Speaker A 轉化為「教授：」，Speaker B 轉化為「提問學生：」，而非死板的 A、B。

### 2. Phase 4 (重點標記) 的防竄改機制 (Anti-Tampering)
LLM (如 Gemma3) 天生喜歡「總結」與「換句話說」。如果丟一萬字給它畫重點，它很容易自作主張刪減內文。
**優化點**：在 P4 的實作中，我們必須在 prompt 加入極度強硬的宣告：`"CRITICAL: 絕對禁止刪減、新增或重寫任何文字！你只能在關鍵字旁加上 ** 前後綴，否則任務直接失敗。"`，並透過 Python 程式去檢驗字數，若字數落差超過 10%，自動退回重做 (Retry)。

### 3. 全局狀態表 (checklist.md) 擴充
由於擴增至 5 個階段，原先的 `checklist.md` 必須變更欄位，加入 `| P1 (轉錄) | P2 (校對) | P3 (合併) | P4 (高亮) | P5 (Notion) |`。

### 4. 資料來源 (Data Lineage) 精確映射
- P1 輸出至 `transcript/`
- P2 讀取 `transcript/` -> 輸出至 `proofread/` (各分段各自獨立，不合併)
- P3 讀取 `proofread/` -> 輸出至 `merged/` (在此合併並排版)
- P4 讀取 `merged/` -> 輸出至 `highlighted/`
- P5 讀取 `highlighted/` -> 輸出至 `notion_synthesis/`

---

## 👩‍💻 使用者互動 UX 優化建議 (UX Optimizations)

程式在執行時，與使用者的互動建議進行以下調整：

### 1. 「一鍵到底」總管模式 (Orchestrator Mode)
目前我們有獨立的 script（如 `transcribe_tool.py`），未來改為 5 階段後，使用者需要手動敲 5 次指令。
**優化點**：建立一支 `run_all.py` (或是更新 Agent 技能)，這支程式會自動一條龍執行 P1 -> P2 -> P3 -> P4 -> P5。當發生中斷時，由於有 checklist 保護，重新啟動會自動跳過已完成的步驟。

### 2. 「中繼站編輯審核」功能 (Human-in-the-loop Checkpoint)
這是學術筆記非常重要的一點！有時 LLM 在 P3 分段時弄錯了某個極重要的名詞，如果 P4、P5 連帶錯下去會很困擾。
**優化點**：當執行腳本時，可以加入一個 `--interactive` 參數。在 P3 (合併分段) 完成後，終端機暫停並提示：`"Phase 3 已完成。您可前往 merged/ 目錄進行人工微調，確認無誤後按 [Enter] 繼續執行 Phase 4..."`。

### 3. [X/Y] 總進度面板顯示 (Dashboard-style Progress)
當進行 5 個 Phase 時，將所有 Phase 的進度彙整成一個動態 Console Dashboard：
```text
=== 執行狀態面板 ===
[P1 轉錄]: ✅ 3/3
[P2 校對]: ✅ 3/3
[P3 合併]: ⏳ 1/2 (處理中...)
[P4 標記]: ❌ 0/2
[P5 筆記]: ❌ 0/2
====================
```

## User Review Required

> [!IMPORTANT]
> 請確認您是否同意上述的 5 階段重構計畫與資料流向？
> 如果您同意，我們後續的執行步驟將會是：
> 1. 更新 `subject_manager.py` 加入新的目錄 (`merged`, `highlighted`) 與 擴充 `checklist.md` 邏輯。
> 2. 拔除 `proofread_tool.py` 現有的合併功能，使其單純進行 P2。
> 3. 新增 `merge_tool.py` (P3) 以及 `highlight_tool.py` (P4)。
> 4. 更新 `notion_synthesis.py` (P5) 使其讀取 P4 的產出。


---

## 2. Walkthrough / Summary

*(No Walkthrough)*

---

## 3. Tasks Executed

# 5-Phase Pipeline Execution Tasks

- [x] **1. Configuration & Scaffolding**
  - [x] Rename output directories to include numerical prefixes (e.g., `01_transcript`, `02_proofread`, `03_merged`, `04_highlighted`, `05_notion_synthesis`) via `subject_manager.py` and physically.
  - [x] Update `subject_manager.py` to support 5 phases in the overall `checklist.md` logic.
  - [x] Update `config.json` to define model names, contexts, and parameters for all 5 phases (phase1, phase2, phase3, phase4, phase5).
  - [x] Update `prompt.md` to include precise, distinct prompts for Phase 2, Phase 3 (including the "助人歷程" multi-speaker logic), Phase 4 (highlight rules without deleting text), and Phase 5.

- [x] **2. Script Refactoring**
  - [x] Add consistent docstrings and inline comments across all scripts.
  - [x] `transcribe_tool.py`: Update to align with uniform structure and `01_transcript`.
  - [x] `proofread_tool.py`: Strip out the merge logic; convert to a pure 1:1 file translation feeding into `02_proofread`.
  - [x] Create `merge_tool.py` (Phase 3): implement `group_tasks_by_lecture`, merge, apply `prompt.md` formatting logic for speakers, output to `03_merged`.
  - [x] Create `highlight_tool.py` (Phase 4): 1:1 file processing applying strong anti-tampering highlighting rules, output to `04_highlighted`.
  - [x] `notion_synthesis.py`: Update to read from `04_highlighted`, output to `05_notion_synthesis`.
  - [x] Create `run_all.py` Orchestrator (Optional/Requested): Implement sequential execution with interactive pause hooks.

- [x] **3. Documentation Updates (English Standard)**
  - [x] Update `voice-memo/PROJECT_RULES.md` to outline the V5.0 5-Phase Architecture.
  - [x] Update `voice-memo/WALKTHROUGH.md` to describe the exact new data flow and reasoning.
  - [x] Update `voice-memo/DECISIONS.md` and `HANDOFF.md` reflecting the new Separation of Concerns philosophy.

