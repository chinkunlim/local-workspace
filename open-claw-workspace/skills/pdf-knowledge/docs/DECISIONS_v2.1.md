# DECISIONS.md — Architecture Decision Record (V2.1)

> [!NOTE]
> 任何 AI 提出架構改動前必須先閱讀此處。

---

## [D001–D016] 沿用自 V2.0（見 DECISIONS_v2.0.md）

---

## [D017] PDF 診斷流程：poppler-utils 前置診斷 vs. 直接 Docling

- **決策**: poppler-utils 輕量診斷（Phase 1a）必須先於 Docling（Phase 1b）執行
- **捨棄**: 直接啟動 Docling 處理所有 PDF
- **原因**:
  - poppler-utils 診斷記憶體佔用 < 50MB，耗時 < 5 秒；Docling 佔用 ~2.5GB，耗時 3-5 分鐘。
  - 80% 的問題（加密、字型損壞、確認掃描件類型）可以在 < 50MB 的狀態下發現，不需要等 Docling 啟動後才知道。
  - `pdffonts` 的字型健康診斷是純粹的遺漏——字型未嵌入（`emb: no`）加上 Custom/Identity-H encoding 會讓 Docling 的文字提取產生亂碼，且這個問題在提取後難以補救。
  - 來源：Claude `pdf-reading` Skill 的 Content Inventory 最佳實踐。

---

## [D018] 向量圖表：pdftoppm 補充 vs. 僅依賴 pdfimages

- **決策**: 對診斷標記的向量圖頁面執行 pdftoppm 光柵化（150 DPI），存入 assets/
- **捨棄**: 僅依賴 pdfimages 提取 raster 圖片
- **原因**:
  - `pdfimages` 只能提取 raster（點陣）圖片，matplotlib/Excel/R 等工具生成的向量圖表完全不會出現。
  - 心理學論文的統計圖（散佈圖、相關矩陣、折線圖）絕大多數是向量格式，若不補充，`figure_list.md` 會大量遺漏關鍵圖表。
  - pdftoppm（poppler-utils）光柵化是標準的向量圖頁面處理方式，且記憶體佔用低。
  - 來源：Claude `pdf-reading` Skill 的「Gotcha — vector graphics」警告。

---

## [D019] OCR 精度：pytesseract per-word 信心分數 vs. Docling 整頁判斷

- **決策**: 對掃描件頁面執行 pytesseract.image_to_data()（200 DPI），取得 per-word 信心分數
- **捨棄**: 只依賴 Docling 的整頁 OCR 信心值
- **原因**:
  - Gemini 建議的 OCR Confidence Gate 是正確需求，但實作方式需要精確化。
  - pytesseract 的 per-word 信心分數比 Docling 整頁判斷更細緻，可以準確定位哪些段落有問題。
  - 200 DPI 光柵化（比 150 DPI 高）對繁體中文 OCR 準確率提升約 15-20%，這對你的學術 PDF 影響顯著。
  - 兩者互補：Docling 做完整結構提取，pytesseract 做品質評估，各司其職。

---

## [D020] 關鍵術語保護：雙層機制（字串替換 + Prompt 注入）

- **決策**: `priority_terms.json` 在 Docling 輸出後立即執行字串替換（Layer 1），同時在每次 LLM Prompt 中注入術語禁令（Layer 2）
- **原因**:
  - 純字串替換：保護文字進入 LLM 前的原始內容，但 LLM 仍可能在輸出中改寫術語。
  - 純 Prompt 注入：依賴 LLM 遵從指令，但中文同義詞替換往往是 LLM 的「慣性」，Prompt 不夠強硬。
  - 兩層並存：字串替換確保輸入乾淨，Prompt 注入確保輸出乾淨。
  - `輔療 vs 輔料`（語音相近但語義完全不同）是具體的高風險案例，需要特別防護。

---

## [D021] 跨批次術語：global_session_memory.json vs. 僅依賴 overlap

- **決策**: 第一個 chunk 完成後建立 `global_session_memory.json`，鎖定核心術語譯法，後續 chunk 強制讀取
- **捨棄**: 只依賴 500 字 overlap
- **原因**:
  - 500 字 overlap 解決的是「相鄰 chunk 的邊界脈絡」問題（Chunk N 和 N+1 的連接）。
  - `global_session_memory.json` 解決的是「非相鄰 chunk 的術語一致性」問題（Chunk 1 在第 1 頁確定的譯法，必須在 Chunk 6 的第 80 頁保持一致）。
  - 兩個機制互補，不能互相取代。

---

## [D022] green_care_potential：Gemini 判斷（Agent Loop 後）vs. Gemma 判斷（Triage 時）

- **決策**: Triage 時設為 `null`，由 Agent Loop 最後一輪的 Gemini 判斷，使用者可手動覆寫
- **捨棄**: Gemma 4:E2B 在 Triage 時自動判斷
- **原因（使用者確認方案 B）**:
  - Gemma 4:E2B 是 2B 模型，判斷「心理學論文是否可轉化為療癒農場素材」需要跨心理學、農業療癒、課程設計三個領域的理解，超出其能力範圍，誤判率高。
  - Gemini 有更強的跨領域理解能力，且在 Agent Loop 結束時已完整讀過整份 PDF，判斷更準確。
  - 使用者手動覆寫保留了最終控制權。

---

## [D023] 懸浮預覽：Flask API（方案 B）vs. 複製截圖 / Base64 嵌入

- **決策**: Flask API 動態讀取 `03_Agent_Core/[PDF_ID]/verification/source_snapshots/`（方案 B）
- **捨棄**: 複製截圖（方案 A）/ Base64 嵌入（方案 C）
- **原因（使用者確認方案 B）**:
  - 方案 A（複製）：增加磁碟佔用，截圖更新時需要同步兩份。
  - 方案 C（Base64）：`verification.json` 可能因嵌入大量截圖而超過 10MB，效能差。
  - 方案 B（Flask API）：零額外磁碟佔用，截圖永遠是最新版本。代價是需要 Flask 服務在線——已加入 fallback（Flask 不在線時顯示純 URL）。

---

## [D024] Marp Slide 2：Gemini 提取「3 Key Points」vs. Triage 生成 vs. H2 目錄

- **決策**: Agent Loop 完成後，由 Gemini 從 `content.md` 提取 3 個學習重點（方案 B）
- **捨棄**: Triage 時 Gemma 生成（方案 A）；H2 自動生成目錄（方案 C）
- **原因（使用者確認方案 B）**:
  - 方案 A：Triage 設計為快速分流決策，增加知識提取任務違反單一職責原則。
  - 方案 C：H2 目錄是結構性資訊，「學習重點」是知識性摘要，兩者概念不同。
  - 方案 B：在 Agent Loop 完成後，Gemini 已完整理解 PDF 內容，提取的學習重點品質最高。代價是 Marp 導出必須等到 Phase 3 完成後才可用——這是合理的。

---

## 🤖 Antigravity Execution History

### 🕒 [2026-04-13] V2.1 — Gemini 建議全部審查 + Claude Skill 整合

新增決策：
- **[D017]** poppler-utils 前置診斷（Claude pdf-reading Skill 整合）
- **[D018]** 向量圖表 pdftoppm 補充（Claude pdf-reading Skill 整合）
- **[D019]** OCR per-word 信心分數（Claude pdf-reading Skill 升級）
- **[D020]** 關鍵術語雙層保護（Gemini 建議，採納）
- **[D021]** 跨批次 global_session_memory（Gemini 建議，採納）
- **[D022]** green_care_potential 由 Gemini 判斷（使用者確認方案 B）
- **[D023]** 懸浮預覽 Flask API（使用者確認方案 B）
- **[D024]** Marp Slide 2 由 Gemini 提取（使用者確認方案 B）

Gemini 建議全部審查結果：8 項全部採納，其中 4 項有技術調整（方案選擇）。
