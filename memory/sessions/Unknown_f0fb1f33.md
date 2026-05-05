# [Archived] Phase 9: Context Window Exceedance Fix

> **Date:** Unknown
> **Session ID:** `f0fb1f33`

---

## 1. Implementation Plan

# Phase 9: Context Window Exceedance Fix

## ⚠️ User Review Required
**Why are the formats still failing and missing Feynman/Cornell/Mermaid?**
I have deeply investigated why the models are still failing to follow the prompt instructions you liked in Phase 7. The reason is a **physical memory limit (Context Eviction)**, not a prompt wording issue. 

Your transcript file `lecture_06.md` is **42,098 characters long** (roughly 15,000 tokens). However, in `config.json`, the `default` profile for Phase 3 does not define a `num_ctx` parameter limit. 
By default, Ollama forces Gemma 3 to run within only **2048 tokens**. When we pass a 15,000 token text, the first 13,000 tokens of the prompt are **automatically deleted from the LLM's memory before it even begins generating**. 
Because the formatting rules (Feynman, Key Learning Points, Mermaid) are written at the very top of the prompt, the model literally never sees them. It only wakes up at the end of the transcript, assumes it should summarize the text, and writes a generic summary.

## Proposed Changes

### config.json
To fix this, we MUST grant the `gemma3:12b` model enough memory to actually "read" the prompt instructions alongside the huge transcript.

#### [MODIFY] config.json
- Open the Phase 3 `default` profile.
- Inject `num_ctx: 16384` into the `options` block.
- Configure `temperature: 0.2` to eliminate LLM creative variance (making it adhere strictly to academic outputs).

## Verification Plan
1. Apply the configuration.
2. Ensure you re-run `python3 py_tools/notion_synthesis.py` on the `lecture_06` audio payload.
3. The model will finally be able to see the flattened Phase 8 list instructions and perfectly generate the Cornell and Feynman blocks.


---

## 2. Walkthrough / Summary

# 語音逐字稿系統 (py_tools) 重構及優化總結

我已經根據計畫完成了 `voice-memo/py_tools` 底下程式碼的改寫與優化。以下是所有變動的總結：

### 1. 新增統一的模型設定檔 `models.md`
我建立了一個全新的設定檔，專供紀錄各階段工具所使用的 LLM 模型名稱及其執行參數：
[NEW] [models.md](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/voice-memo/py_tools/models.md)
透過這個文件，您未來如果需要更換模型名稱或調整任何 temperature、num_ctx 等變數，只需要編輯這個 Markdown 文件，不再需要進去修改 `.py` 檔案內容！

### 2. 優化核心管理員 `subject_manager.py`
[MODIFY] [subject_manager.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/voice-memo/py_tools/subject_manager.py)
在管理程式碼中注入了四大新核心功能：
- **`get_model_config(phase_name)`** 解析 `models.md` 以提供給各腳本讀取參數。
- **`call_ollama(model, prompt, options)`** 將重複出現在各個腳本中的 Request post 及 URL 硬編碼收攏。
- **`should_process_task(task, current_phase_key, previous_phase_key, force)`** 統一判斷邏輯。包含了「是否略過該檔案」、「前置作業是否已完成」、以及「透過 `ask_reprocess` 詢問使用者是否重做」這三種判斷防護網。
- **`get_target_path(base_dir, subj, fname)`** 收攏了所有煩人的路徑組合和 `.m4a` 轉換 `.md` 長字串。

### 3. 三大階段腳本統一
* **[MODIFY] Phase 1:** [transcribe_tool.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/voice-memo/py_tools/transcribe_tool.py) 現在會自動去讀取 `models.md` 裡的 Whisper 模型參數 (包含了 `medium`、`cpu` 裝置以及 `int8` 計算格式)，並且套用了統一防呆函數。 
* **[MODIFY] Phase 2:** [proofread_tool.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/voice-memo/py_tools/proofread_tool.py) 不再寫死 `gemma3:12b` 和 API 網址，轉而使用 `sm.call_ollama()` 來處理 API 的呼叫及異常情況。且它現在也同時採用了最統一的 `sm.should_process_task`（並支援 `force` 強制執行的參數）。
* **[MODIFY] Phase 3:** [notion_synthesis.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/voice-memo/py_tools/notion_synthesis.py) 同等地移除硬編碼，現在它乾淨非常多，核心皆靠 `subject_manager` 來支撐。

---
> [!NOTE]  
> 目前設定已經完整落實您的需求！您可以嘗試執行看看任一階段 (比如 `python transcribe_tool.py` 或 `python proofread_tool.py`) 確保行為如同以往一樣順利。如果您之後需要調整 API 網址，只需在 `subject_manager.py` 開頭的 `OLLAMA_API` 修改一次即可。


---

## 3. Tasks Executed

# Task Checklist: Directory Restructure & Transcription Upgrade

- [ ] Rename physical directories (`audio` -> `raw_data`, `raw_text` -> `transcript`, `crosscheck_text` -> `proofread`, `notion_import` -> `notion_synthesis`).
- [ ] Update directory variables in `subject_manager.py`.
- [ ] Modify `transcribe_tool.py` to output both pure text and timestamped markdown versions.
- [ ] Modify `proofread_tool.py` to fix log outputs and ensure strictly matched PDF mapping.
- [ ] Update Agent historical MD files reflecting the 3rd and 4th changes.

