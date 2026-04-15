# TASKS.md — Roadmap & Backlog (V2.1)

---

## ✅ Completed (Architecture — V2.1)

（包含 V2.0 全部完成項目 + 以下新增）
- [x] 確認 poppler-utils 前置診斷流程（Phase 1a）
- [x] 確認向量圖表 pdftoppm 補充方案
- [x] 確認 OCR 精確模式（pytesseract + 200 DPI + per-word 信心分數）
- [x] 確認 priority_terms.json 雙層術語保護機制
- [x] 確認 global_session_memory.json 跨批次術語一致性
- [x] 確認 green_care_potential = null + Gemini 判斷 + 手動覆寫（方案 B）
- [x] 確認懸浮預覽 = Flask API + URL fallback（方案 B）
- [x] 確認 Marp Slide 2 = Agent Loop 後 Gemini 提取（方案 B）
- [x] 確認 Anki 四欄 Schema（Front/Back/Source/Domain）
- [x] 確認 figure_list.md 數據趨勢標籤（10 種標籤詞彙）
- [x] 整合 Claude pdf-reading Skill（診斷、向量圖、OCR）

---

## 🔴 Active Development — Stage 0: Security + Engine Foundation

### Stage 0.1: Security Foundation（第一優先）
- [ ] **`core/security_manager.py`**: `validate_navigation()` + `validate_action()` + `security_audit.log` + `SecurityViolationError`
- [ ] **`config/security_policy.yaml`**: allowed/forbidden actions 初版，附使用者說明注釋
- [ ] **`core/resume_manager.py`**: `save_checkpoint()` + `check_resumable()` + `resume_from()` + DAG 整合

### Stage 0.2: PDF Engine（含新增腳本）
- [ ] **`pdf_diagnostic.py`**: pdfinfo + pdftotext 採樣 + pdffonts + pdfimages 統計 + 向量圖頁碼偵測 + 多欄偵測
- [ ] **`pdf_engine.py`**: Docling + gc.collect() + 字型損壞 fallback（光柵化驗證）
- [ ] **`vector_chart_extractor.py`**: pdftoppm（150 DPI）+ assets/ + figure_list 標記 type="vector_rasterized"
- [ ] **`ocr_quality_gate.py`**: pytesseract（200 DPI, chi_tra+eng）+ per-word 信心分數 + 0.80 門檻 + scan_report.json

### Stage 0.3: Git Infrastructure
- [ ] **`git_manager.py`**: `git init` + LFS 即時設定（init 後立即執行）+ 統一 commit 介面 + auto-message 格式

### Stage 0 Validation Tests
- [ ] pdffonts 字型損壞偵測（用一份已知有問題的 PDF 測試）
- [ ] pdftoppm 向量圖光柵化（測試統計散佈圖頁面）
- [ ] pytesseract 繁中 OCR 信心分數（用繁中掃描 PDF 測試，確認 chi_tra 語言包安裝）
- [ ] Ctrl+C 中斷後 resume_state.json 正確寫入
- [ ] security_manager 越界攔截測試（嘗試導航到 mail.google.com）

---

## 🟡 Backlog — Phase 0+1: Queue + Extraction

- [ ] **`queue_manager.py`**: 串行 + ModelMutex + health check + 首次啟動設定引導（Chrome Profile 路徑）
- [ ] **`inbox_watcher.py`**: Watchdog + 三層去重（content.md / 佇列中 / MD5）+ 加密偵測
- [ ] **`column_handler.py`**: Gemma 語義連貫性驗證（前5段）+ column_warning 標記
- [ ] **`image_extractor.py`**: PyMuPDF raster 圖片 + caption 匹配（配合 vector_chart_extractor.py 互補）
- [ ] **`reference_injector.py`**: APA/IEEE Regex + 錨點 + refs.bib
- [ ] **`chunk_processor.py`**: H2 邊界 + 500字 overlap + SHA-256 hash + 去重合併
- [ ] **`terminology_builder.py`**: 提取術語 + apply_critical_term_protection() + EN/繁中/Malay + global_session_memory.json 寫入
- [ ] **`main_app.py`**: Flask + Dashboard + WebSocket + 啟動掃描 resume_state + 安全記錄頁籤

---

## 🟡 Backlog — Phase 2: Triage

- [ ] **`triage_agent.py`**: Gemma 4:E2B 分流 + `green_care_potential: null` + `has_statistics` 旗標（觸發統計保護 Prompt）

---

## 🔵 Backlog — Phase 3: Agentic Loop

- [ ] **`playwright_driver.py`**: Persistent Context + security_manager 前置 + Profile 路徑比對確認
- [ ] **`selectors.yaml` 確認**: Gemini 輸入框、Thinking 指示器、Voyager 匯出按鈕（需實際測試）
- [ ] **`agent_loop.py`**: 閉環控制器 + Context Bridge（跨 chunk 脈絡）+ global_session_memory 讀取 + 統計保護 Prompt + green_care 最後一輪判斷
- [ ] **`voyager_handler.py`**: Loop 完成後一次觸發 + 驗證導出完整性 + Gemini 側資料夾歸類
- [ ] **網路中斷偵測 + Thinking 超時**: 5秒 ping + 8分鐘超時 + 截圖 + 人工介入提示

---

## 🔵 Backlog — Phase 4: Fact-Check

- [ ] **`whitelist_guard.py`**: 兩層核實邏輯 + verification.json
- [ ] **`chroma_manager.py`**: multilingual embedding benchmark（D016）+ 向量化 + 相似度比對
- [ ] **`figure_describer.py`**: Gemma VLM + domain-aware + **數據趨勢標籤**（10 種詞彙）+ figure_list.md 更新
- [ ] **引用 URL 快照**: Playwright 後台截取 → source_snapshots/

---

## 🟢 Backlog — Phase 5: Interactive Interface

- [ ] **`editor.html`**: 離線 Vditor + MathJax v3 + [?] 警告框 + OCR 品質警告渲染 + **[G:URL] 懸浮預覽**（Flask API + URL fallback）
- [ ] **Flask API `/api/source_preview`**: 根據 URL hash 找 source_snapshots/ 截圖並返回
- [ ] **Markmap 整合**: H1/H2/H3 → 思維導圖
- [ ] **Git Diff + Log + 版本回溯**
- [ ] **Antigravity Panel**: 三版建議 + adopt → git commit
- [ ] **Dashboard V2**: 安全記錄頁籤 + 三種操作模式 + green_care 手動標記 + OCR 警告列表
- [ ] **`export_engine.py`**: Marp（含 Slide 2 Gemini 提取接口）+ Anki（四欄 Schema + 原始句子提取）

---

## ⬛ Future Extensions

- [ ] 生活養雞學情境轉譯器（green_care_potential == true 自動觸發）
- [ ] 跨文件知識圖譜 Auto-Wiki
- [ ] Dashboard 全文搜尋 + 數據趨勢標籤篩選
- [ ] Telegram Bot 整合

---

## ❓ Pending — 待使用者確認

- [ ] **[Q001]** ChromaDB embedding 模型（D016，需 benchmark）
- [ ] **[Q002]** 繁中 PDF 測試樣本
- [ ] **[Q003]** Chrome Profile 路徑
- [ ] **[Q004]** Voyager 資料夾名稱是否足夠
- [ ] **[Q005]** 「簡單文件」具體例子
- [ ] **[Q006]** Anki 導出：自動 vs 手動觸發
- [ ] **[Q007]** `priority_terms.json` 初版術語清單是否完整？有無其他 「輔療/輔料」類型的高風險術語？

---

## 🤖 Antigravity Execution History

### 🕒 [2026-04-13] V2.1 — Gemini 建議審查 + Claude Skill 整合
- [x] 審查 Gemini 8 項建議：全部採納，4 項有技術調整
- [x] 整合 Claude pdf-reading Skill 的三大影響（D017/D018/D019）
- [x] 新增 Stage 0.2 的 pdf_diagnostic.py 和 vector_chart_extractor.py
- [x] 確認使用者對 4 個問題的選擇（B/安全方案/B/B）
- [x] 新增 Q007（priority_terms 完整性）

### 🕒 [2026-04-15] V2.2 — Dual-Skill Alignment & Dependency Bootstrap
- [x] 建立全域 macOS `bootstrap.sh` 安裝所有依賴 (`flask`, `docling`, `pypdf`, 等)。
- [x] 明確了與 `voice-memo` 對齊的共用守則（State Manager, Enum Logs, OOP Inheritance）。
- [x] 吸納 `core/text_utils.py` 分塊工具至全域。
