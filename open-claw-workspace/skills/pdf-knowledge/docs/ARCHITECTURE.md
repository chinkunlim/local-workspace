# PDF Knowledge Skill — Architecture & Feature Spec

這份文件記錄了 **PDF Knowledge Pipeline** 專屬的 PDF 文件處理技術框架、圖形/欄位解構機制與資料流向。全域的開發標準請參閱專案根目錄 `docs/CODING_GUIDELINES.md`。

---

## 📑 PDF 解析三部曲 (The 3-Step Extraction Philosophy)

為預防 PDF 各式不規範的加密、錯版或掃描檔佔用高昂資源，本系統強制以下流程：

### 1. 輕量診斷 (Diagnostic pre-flight)
- **工具**：`poppler-utils` (`pdfinfo`, `pdffonts`, `pdfimages`)。
- **目的**：5 秒內攔截無文字的掃描件、壞掉的字型編碼 (Identity-H)、以及抓出潛在的亂碼與雙欄佈局。
- 診斷結果被統整進 `scan_report.json`，供子系統查閱並決策是否能進入下一步。

### 2. 深度提取 (Docling Deep Extraction)
- **觸發**：診斷認定無誤後執行。
- **目標**：結構化剖析 Heading 邊界、處理文獻標示與斷行規則。

### 3. 向量圖表補充與 OCR 光柵 (Vector / Raster Validation)
- 處理 `poppler` 未抓出的向量圖表，使用 `pdftoppm` 精準擷取。
- 對於診斷抓出的低信心頁面，拉高 DPI 重作 Tesseract OCR，並進行語義長度驗證 (Fallback機制)。

---

## 🔒 資訊提取安全網 (Context & Security Guard)

1. **Playwright 零污染憑證保護**
   - 堅決不動用 `accounts.google.com` 在 headless 內的存取！預覽或搜集網頁資訊利用既有的本地 Persistent Profile 處理。
   - 所有跳轉網址必須通過內部 `security_policy.yaml` 路由驗證，阻攔惡意跨站追蹤。
2. **多欄與公式防護 (Equation & Column Protection)**
   - 雙欄 PDF 若引發 Docling 失準，立即掛起 `column_handler.py` (語義檢測法)。
   - 統計數據 (p-value, F-test 等) 使用 LaTeX 安全層級進行防改寫置換 `[LATEX_N]`，預防 LLM 在修飾語句時將數字「圓整」或造假。

---

## 🤝 使用者處理介面流 (Intervention Modes)

系統區分三種處理介入層級：
1. **全自動模式**：完全順跑佇列。
2. **暫停模式**：執行完目前 PDF 工作後，立即駐停並掛起 Checkpoint，直到獲得命令。
3. **人工接管 (Manual Handover)**：Chrome 面板進入前台，由操作者與網頁直接互動對話，完成人工判定後「交回系統」。
