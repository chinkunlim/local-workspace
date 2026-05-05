# [Archived] Goal Description

> **Date:** Unknown
> **Session ID:** `f9bb2404`

---

## 1. Implementation Plan

# Goal Description

The objective is to introduce two powerful features into the Open-Claw `voice-memo` pipeline:
1. **Targeted Subject Execution**: Allow the orchestrator (`run_all.py`) and individual phase tools to process tasks for a specific subject only, utilizing a `--subject <SubjectName>` flag.
2. **Subject-based Config Auto-switching**: Introduce a `"subject_overrides"` dictionary mechanism in `config.json` so that the pipeline dynamically swaps LLM profiles (e.g., using `qwen3_chinese` for "助人歷程" and `strict_gemma` for pure English "生理心理學") without manual intervention.

## Proposed Changes

---

### `core/pipeline_base.py`

Modify the foundational class methods to support subject filtering and dynamic config retrieving.

#### [MODIFY] `pipeline_base.py`
- Modify `get_tasks(self, prev_phase_key=None, force=False, subject_filter=None)`:
  - Introduce logic to only yield tasks matching `subject_filter` if it is provided.
- Modify `get_config(self, phase_name: str, subject_name: str = None)`:
  - If `subject_name` is provided, look up `phase_config.get("subject_overrides", {})`. If a match is found, replace `active_profile` with the override profile before fetching profile parameters.

---

### Phase Scripts (`transcribe_tool.py`, `proofread_tool.py`, etc.)

Since configuration settings (like `model` and `chunk_size`) will now depend on the subject being iterated over, the model configuration fetching must happen *inside* or intelligently *around* the task iteration loop.

#### [MODIFY] All Phase Tools (0 to 5)
- Update `run(self, force=False, subject=None)` signature.
- Pass `subject_filter=subject` into `self.get_tasks(...)`.
- Move the `config = self.get_config("phaseX", subject_name=subj)` logic *inside* the task execution loop so it accurately scales to the subject being processed.
- Collect all dynamically used model names in a `set()`, and at the end of the script, unload all models used in that run using `self.llm.unload_model`.

---

### `run_all.py`

Expose the targeted parameter so the user has CLI control.

#### [MODIFY] `run_all.py`
- Add `-s / --subject` argument to `argparse`.
- Route `args.subject` into `Phase0Glossary().run(...)` and `p_obj.run(...)` calls.

---

### `config.json` Schema Enhancement

Inject the structural support required for auto-switching.

#### [MODIFY] `config.json`
- Apply `"subject_overrides"` block to `phase2`, `phase3`, and `phase5` to dictate that "生理心理學" correctly invokes `strict_gemma` (or `gemma4_e4b` in P5) and "助人歷程" invokes `qwen3_chinese` / `qwen_chinese`. Example:
```json
"phase2": {
    "active_profile": "strict_gemma",
    "subject_overrides": {
        "生理心理學": "strict_gemma",
        "助人歷程": "qwen3_chinese"
    },
    ...
```

## Open Questions

- If an override is set in `config.json` but doesn't exist in `profiles`, does it gracefully fallback to `active_profile` or `default`? (I will ensure the code defaults safely).

## Verification Plan

### Automated Tests
- Review the `config.json` schema updates statically.

### Manual Verification
- Run `python run_all.py --subject 生理心理學 --force --from 2` to verify that `pipeline_base.get_tasks()` correctly filters only `生理心理學`.
- Observe system CLI stdout logs to ensure it activates `gemma` for the English course due to `subject_overrides` behavior.


---

## 2. Walkthrough / Summary

# 專案實作完成：Subject 指向與設定檔動態切換 🚀

我們已經成功將「科目單獨執行 (`--subject`)」以及「依據科目自動切換參數 (`subject_overrides`)」這兩大進階功能深度整合到 Open-Claw 的 voice-memo Pipeline 之中！

以下為本次實作的重點導覽與使用手冊：

## 1. 設定檔的動態切換 (`config.json`)

我們在 `config.json` 的架構中引入了全新的 `subject_overrides` 區塊，賦予了 Pipeline 判斷與調度模型的能力。

現在，在你的 `phase2`, `phase3`, 以及 `phase5` 的設定裡，你可以這樣寫：

```json
  "phase2": {
    "active_profile": "qwen3_chinese",
    "subject_overrides": {
      "生理心理學": "strict_gemma",
      "助人歷程": "qwen3_chinese"
    },
    ...
```

**運作邏輯**：
- 當 Pipeline 處理到「生理心理學」的錄音時，它會自動將 Phase 2 的模型從預設的 `qwen3_chinese` **強行切換為**擅長處理英文文本的 `strict_gemma`。
- 如果某個科目沒有被列在 `subject_overrides` 裡，則會退回到 `active_profile` 預設的 Profile。
- 這個切換是在「檔案迭代迴圈」中**即時**發生的，意思是你就算跑 `run_all.py` (不鎖定任何科目)，它也能正確在跑到不同的科目時**隨時抽換模型**，做到最高效能的處理！

## 2. 獨立執行指定科目 (`--subject`)

現在 Orchestrator (`run_all.py`) 與所有底層的 Phase 工具 (0~5)，都全面支援了全新的 `-s` / `--subject` 指令。

### 下達指令的方式

如果你今天只想針對「生理心理學」進行處理，可以直接執行：

```bash
python3 scripts/run_all.py --subject 生理心理學 --force
```

**這個 `--subject` 會一層一層傳遞給所有的子工具**：
1. **Phase 0 (詞庫庫)** 只會處理該科目。
2. **Phase 1~5** 裡面的 DAG State Manager 會讀取這個設定，在 `get_tasks` 取出待辦清單時，濾除所有其他的資料夾，保證不會誤動其他學科。

> [!TIP]
> 甚至，你可以單獨呼叫某一個腳本進行測試：
> ```bash
> python3 scripts/proofread_tool.py --subject 生理心理學 --force
> ```

## 3. 防範記憶體溢出機制 (Unload)

這是一個架構上的巨大挑戰：因為系統能在同一次執行中動態切換多個大型模型（如 `qwen3` -> `gemma3`），這很容易導致 VRAM/RAM 爆炸。

**解法**：我已經在各個腳本 (從 Glossary 到 Notion Synthesis) 中埋入了追蹤器 (`models_used`)。腳本會精準記錄它在這個階段呼叫過哪些模型，並在處理完畢後，發出 `unload_model` 清空所有載入的權重檔，保證下一個 Phase 啟動時擁有滿血的 RAM。


---

## 3. Tasks Executed

- [x] Create `subject_overrides` schema in `config.json`.
- [x] Update `core/pipeline_base.py` (`get_config`, `get_tasks`)
- [x] Update `run_all.py` (add `--subject` CLI flag)
- [x] Update `glossary_tool.py` (Phase 0)
- [x] Update `transcribe_tool.py` (Phase 1)
- [x] Update `proofread_tool.py` (Phase 2)
- [x] Update `merge_tool.py` (Phase 3)
- [x] Update `highlight_tool.py` (Phase 4)
- [x] Update `notion_synthesis.py` (Phase 5)

