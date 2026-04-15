---
name: pdf-knowledge
description: >
  全本機、混合智能的學術 PDF 知識提取與合成系統。
  大量投入 PDF（心理學、IT、課程設計），
  自動輸出可編輯、版本控制、引用核實的 Markdown 知識庫。
---

# PDF Knowledge Skill (V2.2 — Stage 0.2 Active)

將 PDF 放入 `01_Inbox/`，系統自動完成：診斷 → 提取 → 圖表補充 → OCR 品質評估 → Gemini 代理分析。

**Data Lineage**:
`input/01_Inbox/` → `output/02_Processed/` → `output/03_Agent_Core/` → `output/05_Final_Knowledge/`

**State / Logs**:
`state/` · `logs/system.log` · `logs/dashboard.log`

**Workspace root**: `/Users/limchinkun/Desktop/local-workspace/open-claw-workspace`

---

## ⚙️ First-Time Setup（首次使用必讀）

### 1. 安裝依賴
```bash
# poppler-utils（PDF 診斷，必要）
brew install poppler

# Python 套件
pip install docling pymupdf pdfplumber pytesseract pillow watchdog flask pyyaml

# Tesseract OCR + 繁中語言包
brew install tesseract tesseract-lang
```

### 2. 填寫 Chrome Profile 路徑（Playwright 功能需要）
編輯 `skills/pdf-knowledge/config/config.yaml`：
```yaml
playwright:
  chrome_profile: "/Users/limchinkun/Library/Application Support/Google/Chrome/Default"
  account_hint: "你的帳號備忘"
```

### 3. 確認安全邊界
`config/security_policy.yaml` — 只允許前往 `gemini.google.com`，禁止 Gmail/Drive/帳號設定。

---

## 🚀 Dashboard（推薦操作方式）

```bash
cd /Users/limchinkun/Desktop/local-workspace/open-claw-workspace
python3 skills/pdf-knowledge/scripts/main_app.py
```

開啟瀏覽器前往 `http://127.0.0.1:5001`

---

## 📋 Stage 0: PDF Extraction Pipeline

### Phase 1a — 輕量診斷（≤ 50MB RAM，≤ 5秒）
```bash
cd /Users/limchinkun/Desktop/local-workspace/open-claw-workspace
python3 skills/pdf-knowledge/scripts/pdf_diagnostic.py <PDF路徑> [--id <PDF_ID>]
```
- 輸出：`data/pdf-knowledge/02_Processed/<PDF_ID>/scan_report.json`
- 診斷：頁數/加密/掃描偵測/字型健康/向量圖頁碼/多欄

### Phase 1b — Docling 深度提取（~2.5GB RAM）
```bash
python3 skills/pdf-knowledge/scripts/pdf_engine.py <PDF路徑> [--id <PDF_ID>]
```
- 輸出：`data/pdf-knowledge/02_Processed/<PDF_ID>/raw_extracted.md`（IMMUTABLE）
- 自動執行：字型損壞 fallback + 術語 Layer 1 替換

### Phase 1c — 向量圖表補充
```bash
python3 skills/pdf-knowledge/scripts/vector_chart_extractor.py <PDF路徑> --id <PDF_ID> --from-report
```
- 輸出：`assets/fig_p{N}_vector.jpg` + `figure_list.md` 更新

### Phase 1d — OCR 品質評估
```bash
python3 skills/pdf-knowledge/scripts/ocr_quality_gate.py <PDF路徑> [--id <PDF_ID>]
```
- 輸出：更新 `scan_report.json` 的 `low_confidence_pages`

### Phase 0 — 佇列管理（整合執行 1a→1b→1c→1d）
```bash
python3 skills/pdf-knowledge/scripts/queue_manager.py --process-all
python3 skills/pdf-knowledge/scripts/queue_manager.py --scan       # 只掃描不處理
python3 skills/pdf-knowledge/scripts/queue_manager.py --process-one  # 只處理下一個
```

---

## 👁️ Inbox 監視
```bash
python3 skills/pdf-knowledge/scripts/inbox_watcher.py
```
自動監控 `data/pdf-knowledge/01_Inbox/`，偵測到新 PDF 自動觸發處理。

---

## User Intent & Invocation

當使用者發送以下請求時，對應執行：

| 使用者意圖 | 操作 |
| :--- | :--- |
| *「開啟 PDF 儀表板」* / *「Start PDF dashboard」* | `main_app.py`（開啟 `http://127.0.0.1:5001`）|
| *「處理 PDF」* / *「把 PDF 放入 Inbox」* | 確認 PDF 在 `01_Inbox/`，然後 `queue_manager.py --process-all` |
| *「診斷這個 PDF」* / *「Diagnose PDF」* | `pdf_diagnostic.py <路徑>` |
| *「提取 PDF 內容」* / *「Extract PDF」* | `pdf_engine.py <路徑>` |
| *「補充向量圖表」* | `vector_chart_extractor.py <路徑> --from-report` |
| *「評估 OCR 品質」* | `ocr_quality_gate.py <路徑>` |
| *「有哪些未完成的 PDF？」* | `curl http://127.0.0.1:5001/resume` 或問 Dashboard |
| *「更新術語保護清單」* | 提示使用者編輯 `config/priority_terms.json`（AI 不直接寫入）|

---

## Notes

- **安全邊界**：所有 Playwright 操作在 `core/security_manager.py` + `config/security_policy.yaml` 授權下執行。
  Dashboard「安全記錄」可查詢 `output/03_Agent_Core/{PDF_ID}/security_audit.log`。
- **斷點續傳**：中斷後重啟，系統自動從 `resume_state.json` 繼續。
- **IMMUTABLE**：`raw_extracted.md` 禁止任何修改（任何 AI 均不得修改此檔案）。
- **術語保護**：`config/priority_terms.json` 只有使用者可直接修改。AI 可建議，需使用者確認。
- **硬體安全**：可用 RAM < 500MB 自動暫停；< 200MB 強制停機。
- **共用框架**：繼承 workspace root `core/` 的 `PipelineBase`（skill_name="pdf-knowledge"）。
- **Shared Core 位置**：`/Users/limchinkun/Desktop/local-workspace/open-claw-workspace/core/`
