# Voice Memo Skill — Architecture & Feature Spec

這份文件記錄了 **Voice Memo Pipeline** 專屬的業務邏輯、防禦參數設定與五大生命週期。若需了解全域系統的開發標準，請參照根目錄 `docs/CODING_GUIDELINES.md`。

---

## 🔄 核心管線：五階段生命週期 (5-Phase Pipeline)

本套件的音訊文字化管線切分為 5 大不可分割、並具備防呆機制的操作階段：

1. **Phase 1: Transcribe (轉錄)**
   - 利用 `mlx-whisper` 或 `faster-whisper` 等原生高算力解碼方案，進行原始音檔 (.m4a) 解析。
2. **Phase 2: Proofread (學術校對)**
   - LLM 直接比對 PDF 課程資料進行內容校正，修正發音與專有名詞。
3. **Phase 3: Denoising & Merge (對話合併與除噪)**
   - 清除冗言贅字 (uh, um)，並針對多位講者的對話邏輯自動段落化與語境整合。
   - 預設合併閥值 `P3_VERBATIM_THRESHOLD = 0.70`，確保不破壞文意。
4. **Phase 4: Non-Destructive Highlight (無損重點標記)**
   - 採用 Markdown 標記符 `==highlight==`，由 LLM 自動抓取定義或精華，不刪減原始文字。
   - 高敏感防竄改守衛：輸出差異字數檢驗。
5. **Phase 5: Knowledge Synthesis (高可用知識合成)**
   - 採集所有前置資訊，利用 Map-Reduce (對應超長文本) 建構出：**3 大學習重點摘要、Cornell 筆記格式、QEC 分析框架、Mermaid 概念心智圖，以及 Feynman 類比解說**。

---

## 🛡️ 領域特性：專有名詞保護

1. **Phase 0: Glossary Auto-Generation (自動字典庫建立)**
   - 本地專用腳本，從原始材料爬取專有名詞生出系統字典，未來 Pipeline 執行時將被強制套用以預防 Whisper 或 LLM 的拼字錯誤。
2. **文字防護牆 (Text Integrity)**
   - 設計任何 Pipeline 更新時，都必須誓死保持原講者風格與字數流暢性，任何不允許的刪減都會被 `anti-tampering` 強制還原。
