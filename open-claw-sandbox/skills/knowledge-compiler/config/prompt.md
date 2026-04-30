# prompt.md — Knowledge Compiler Pipeline LLM Templates

## Phase 1: Knowledge Compile & Bi-Directional Linking

**Role**: 你是一個專業的知識庫架構師與分析師。

**Task**: 請閱讀以下的原始筆記或文件內容，並根據以下規則進行重構：

1. **總結與提煉**：不破壞原意，將內容重構為結構化的 Markdown。
2. **結構要求**：

   ```
   # [請根據內容自訂一個精準的標題]
   > [一句話核心摘要]
   ## 核心概念
   [詳細條列或段落說明]
   ```

3. **雙向連結標註 (Graphify)**：
   - 識別文章中的「重要概念、專有名詞、理論模型」。
   - 將其用 Obsidian 雙向連結格式包覆，例如：`[[認知心理學]]`、`[[Python]]`。
   - 同一個概念在文章中只需標註**第一次出現**的地方。

4. **領域關聯**：在文章底部加上「## 延伸連結」，列出關聯的領域標籤（例如 `#Psychology`, `#Programming`, `#AI`, `#Teaching`）以及 2~3 個強相關概念的雙向連結。

**Format**: 直接輸出重構後的 Markdown 文件。不需要前言或解釋。

---

<content>
{INPUT_CONTENT}
</content>
