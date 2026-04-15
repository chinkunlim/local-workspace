# HANDOFF.md — Execution State Tracker (V2.1)

> [!IMPORTANT]
> ## Current State: V2.2 — Environment Bootstrapped & Guidelines Aligned. Ready for Phase 0 Coding.

---

## 所有已確認的設計決策快照

| 決策 | 方案 | ADR |
| :--- | :--- | :---: |
| PDF 診斷先行（poppler-utils）| Phase 1a 先於 Docling | D017 |
| 向量圖表補充（pdftoppm）| 對向量圖頁面光柵化存入 assets/ | D018 |
| OCR 精度（pytesseract 200 DPI）| per-word 信心分數 + 0.80 門檻 | D019 |
| 術語雙層保護 | priority_terms.json + Prompt 注入 | D020 |
| 跨批次一致性 | global_session_memory.json | D021 |
| green_care_potential | null→Gemini 判斷→使用者覆寫 | D022 |
| 懸浮預覽 | Flask API + URL fallback | D023 |
| Marp Slide 2 | Agent Loop 後 Gemini 提取 | D024 |
| Voyager 時序 | Loop 完成後一次觸發 | D008 |
| 安全邊界 | security_policy.yaml + Profile 路徑比對 | D010/D011 |
| 斷點續傳 | resume_state.json + DAG | D012 |
| Core Framework | 繼承 Voice Memo core/ | D014 |

---

## Immediate Next Steps（開發優先順序）

### Stage 0.1 — Security Foundation（先於一切）
1. `core/security_manager.py`（授權邊界 + 審計日誌）
2. `config/security_policy.yaml`（初版）
3. `core/resume_manager.py`（斷點續傳）

### Stage 0.2 — PDF Engine
4. `pdf_diagnostic.py`（poppler-utils 診斷）
5. `pdf_engine.py`（Docling + gc.collect()）
6. `vector_chart_extractor.py`（pdftoppm 向量圖補充）
7. `ocr_quality_gate.py`（pytesseract 信心分數）

### Stage 0.3 — Git Infrastructure
8. `git_manager.py`（init + LFS 即時設定 + commit 介面）

### Phase 0+1 — Queue + Complete Extraction
9. `queue_manager.py`（串行 + ModelMutex + health check + 首次設定引導）
10. `inbox_watcher.py`（Watchdog + 三層去重 + 加密偵測）
11. `column_handler.py`（Gemma 語義連貫性驗證）
12. `image_extractor.py`（PyMuPDF raster 圖片 + caption）
13. `reference_injector.py`（APA/IEEE + 錨點 + refs.bib）
14. `main_app.py`（Flask + Dashboard + resume_state 掃描）

---

## 使用者在開始實作前需確認

- [ ] **Q003**: Chrome Profile 路徑（`chrome://version/`）→ `config.yaml`
- [ ] **Q004**: Voyager 資料夾名稱是否足夠（psychology/it/curriculum）？
- [ ] **Q005**: 「簡單文件」例子（讓 Triage 分流更準確）

---

## 已解決問題完整記錄（累計）

| 問題 | 解決方案 | 版本 |
| :--- | :--- | :---: |
| Voyager 時序 | Loop 後一次觸發 | V1.1 |
| 多欄 PDF | Docling Layout + Gemma 驗證 | V1.1 |
| 大型 PDF 分批 | H2 邊界 + 500字 overlap | V1.1 |
| 加密 PDF | fitz + 空密碼嘗試 | V2.0 |
| 重複 PDF | 三層去重 | V2.0 |
| 跨 Session 脈絡 | Context Bridge | V2.0 |
| 安全邊界 | security_policy.yaml | V2.0 |
| 斷點續傳 | resume_state.json | V2.0 |
| 多帳號防呆 | Profile 路徑比對（不存取 Google 頁面）| V2.0 |
| Git LFS | init 後立即設定 | V2.0 |
| 字型損壞 PDF | pdffonts 診斷 + 光柵化 fallback | V2.1 |
| 向量圖表遺漏 | pdftoppm 光柵化補充 | V2.1 |
| OCR 品質 | pytesseract per-word 信心分數 | V2.1 |
| 術語誤用（輔療）| priority_terms.json 雙層保護 | V2.1 |
| 跨批次術語衝突 | global_session_memory.json | V2.1 |
| 統計數據被改 | LaTeX 函數保護 + Prompt 禁令 | V2.1 |
| green_care 接口 | triage null + Gemini 判斷 + 手動覆寫 | V2.1 |
| 懸浮預覽截圖 | Flask API + URL fallback | V2.1 |
| Anki Schema 缺失 | 完整四欄 Schema 定義 | V2.1 |
| Marp Slide 2 | Agent Loop 後 Gemini 提取 | V2.1 |
