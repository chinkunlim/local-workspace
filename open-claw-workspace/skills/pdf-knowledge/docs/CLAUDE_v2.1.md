# CLAUDE.md — OpenClaw PDF Knowledge Skill (V2.1)

> [!IMPORTANT]
> **V2.1 變更**: 整合 Gemini 補強建議（8項全部確認）+ Claude `pdf-reading` Skill 整合（診斷升級、OCR 精度、向量圖表處理）。所有決策均有明確的技術依據。

---

## Project Identity

全本機、混合智能的學術 PDF 知識提取與合成系統。大量投入 PDF（心理學、IT、課程設計），自動輸出可編輯、版本控制、引用核實的 Markdown 知識庫。

**五大設計原則**:
1. **斷點不失作** — 任何中斷後重啟，自動從上次成功的狀態繼續
2. **人機共存** — 三種操作模式（自動/暫停/接管）無縫切換
3. **安全第一** — Playwright 在嚴格授權邊界內操作，帳號憑證零接觸
4. **共用勝於重造** — 繼承 Voice Memo `core/` 框架
5. **診斷先行** — 輕量診斷（poppler-utils）先於重量處理（Docling），提前發現問題

---

## Shared Core Framework（與 Voice Memo Skill 整合）

| 組件 | Voice Memo 用途 | PDF Skill 複用方式 |
| :--- | :--- | :--- |
| `pipeline_base.py` | Phase 0-5 OOP 基底 | 所有 Phase 腳本繼承 |
| `state_manager.py` | DAG SHA-256 cascade invalidation | PDF Phase 狀態管理 |
| `llm_client.py` | Ollama HTTP wrapper，retry，keep_alive:0 | Gemma 4:E2B 呼叫 |
| `check_system_health()` | RAM/Temp/Battery 防禦 | 直接複用，同一組 macOS 閾值 |

**PDF Skill 貢獻回 `core/`**（跨 Skill 通用）:
- `security_manager.py` — Playwright 授權邊界
- `resume_manager.py` — 跨 Session 斷點續傳

---

## Tech Stack

| Layer | Technology | 來源 |
| :--- | :--- | :---: |
| **OOP / DAG / LLM / Health** | `core/` framework | 🔄 共用 |
| **PDF 診斷（輕量前置）** | poppler-utils（`pdfinfo`, `pdftotext`, `pdfimages`, `pdffonts`）| 🆕 Claude pdf-reading Skill |
| **PDF 結構提取（重量）** | Docling (IBM) | 🆕 PDF Skill |
| **圖片提取（Raster）** | PyMuPDF (fitz) — `get_images()` | 🆕 PDF Skill |
| **圖片提取（向量轉 Raster）** | pdftoppm（poppler-utils）| 🆕 Claude pdf-reading Skill |
| **表格提取** | pdfplumber | 🆕 Claude pdf-reading Skill |
| **OCR（精確模式）** | pytesseract + pdftoppm | 🆕 Claude pdf-reading Skill |
| **OCR（整合模式）** | PaddleOCR via Docling | 🆕 PDF Skill |
| **字型診斷** | pdffonts（poppler-utils）| 🆕 Claude pdf-reading Skill |
| **Local LLM** | Ollama `gemma4:e2b` | 🆕 PDF Skill |
| **Browser Agent** | Playwright (Python) | 🆕 PDF Skill |
| **Security** | `security_manager.py` | 🆕 PDF Skill → core/ |
| **Resume** | `resume_manager.py` | 🆕 PDF Skill → core/ |
| **Gemini Access** | Web UI only（gemini.google.com）| 🆕 PDF Skill |
| **Voyager Plugin** | Chrome Extension v1.3.9 | 🆕 PDF Skill |
| **版本控制** | GitPython，per-PDF repo，Git LFS | 🆕 PDF Skill |
| **向量 DB** | ChromaDB + multilingual embedding（待 D016 確認）| 🆕 PDF Skill |
| **Frontend** | Flask + Vditor + Markmap | 🆕 PDF Skill |

---

## Security Architecture

> [!WARNING]
> Playwright 操控真實 Chrome 和 Google 帳號，必須在嚴格授權邊界內執行。

### 操作授權邊界（`config/security_policy.yaml`）

```yaml
allowed_actions:
  navigate:
    - "gemini.google.com/*"
    - "gemini.google.com/gems/*"
  interact:
    - "gemini.google.com/app/*"
  download:
    - path: "~/Downloads/"
      file_types: [".md", ".json"]

forbidden_actions:
  - "*.google.com/settings/*"
  - "mail.google.com/*"
  - "drive.google.com/*"
  - "accounts.google.com/*"    # 禁止，防止帳號驗證導致存取 Google 帳號頁面
  - "click: logout"
  - "access_cookies: true"
  - "screenshot_outside_gemini: true"
  - "fill_credentials: true"
```

### 多帳號防呆（Profile 路徑比對，不存取 Google 頁面）

```yaml
# config/config.yaml
playwright:
  chrome_profile: "/Users/.../Chrome/Default"  # ⭐ 首次啟動前填入
  account_hint: "work account"                  # 備忘欄位，啟動時顯示給使用者肉眼確認
  # 系統比對 Profile 路徑名稱（如 "Profile 1"），不讓 Playwright 存取 accounts.google.com
```

啟動時顯示：`✅ Chrome Profile: Default — 備忘: "work account"。這是你想要使用的帳號嗎？[是/否]`

### 安全審計日誌（`security_audit.log`）
```
[TIMESTAMP] [ACTION] [ALLOWED/BLOCKED] → [TARGET]
[2026-04-13T14:30:01] [NAVIGATE] [ALLOWED] → https://gemini.google.com/app
[2026-04-13T14:32:00] [CLICK]    [ALLOWED] → Voyager export button
```

---

## PDF Processing Pipeline（升級版，整合 pdf-reading Skill）

### 關鍵設計決策：診斷先行

```
Phase 1 重新設計為三個子步驟:
  1a. 輕量診斷（poppler-utils）— 快速、低記憶體，提前發現問題
  1b. 深度提取（Docling）— 重量，僅在 1a 無問題後啟動
  1c. 向量圖表補充（pdftoppm）— 對 1a 中偵測到無法提取的向量圖頁面光柵化
```

### Phase 1a：輕量診斷（`pdf_diagnostic.py`，新增腳本）

```python
def run_diagnostics(pdf_path: str) -> DiagnosticReport:
    """
    在 Docling 啟動前執行，快速判斷 PDF 性質。
    工具：poppler-utils（pdfinfo, pdftotext, pdfimages, pdffonts）
    記憶體佔用：< 50MB（Docling 的 2.5GB 的 2%）
    """
    report = {}

    # 1. 基礎資訊
    report["meta"] = run_pdfinfo(pdf_path)         # 頁數、版本、加密狀態
    report["pages"] = int(report["meta"]["Pages"])
    report["encrypted"] = report["meta"].get("Encrypted") == "yes"

    # 2. 文字可提取性（掃描偵測）
    first_page_text = run_pdftotext_sample(pdf_path, pages=1)
    report["is_scanned"] = len(first_page_text.strip()) < 50

    # 3. 字型健康診斷（新增！防止 Docling 在損壞字型上產生亂碼）
    font_info = run_pdffonts(pdf_path)
    report["has_broken_fonts"] = any(
        f["emb"] == "no" and f["encoding"] in ["Custom", "Identity-H"]
        for f in font_info
    )
    if report["has_broken_fonts"]:
        logger.warning("⚠️ 偵測到未嵌入字型，文字提取可能產生亂碼，建議頁面光柵化")

    # 4. 圖片統計（含向量圖表偵測）
    image_list = run_pdfimages_list(pdf_path)
    report["has_raster_images"] = len(image_list) > 0
    # 向量圖表無法被 pdfimages 偵測，改用頁面大小與文字密度的交叉判斷
    report["vector_chart_pages"] = detect_vector_chart_pages(pdf_path)

    # 5. 多欄偵測（pdftotext -layout 的行寬分析）
    report["likely_multi_column"] = detect_multi_column(pdf_path)

    return report
```

### Phase 1b：深度提取（Docling，僅在診斷通過後）

對於 `has_broken_fonts: true` 的 PDF，Docling 提取後強制進行頁面光柵化驗證（`pdftoppm` → 人工確認）。

### Phase 1c：向量圖表補充（`vector_chart_extractor.py`，新增腳本）

```python
def extract_vector_charts(pdf_path: str, page_nums: List[int]) -> List[str]:
    """
    pdfimages 看不到 matplotlib/Excel/R 的向量圖。
    解決方案：對這些頁面執行 pdftoppm 光柵化（150 DPI），
    存入 assets/ 並在 figure_list.md 標記 "vector_rasterized"。
    這確保心理學論文的統計圖（散佈圖、迴歸圖）不會被漏掉。
    """
    saved = []
    for page_num in page_nums:
        output = run_pdftoppm(pdf_path, page=page_num, dpi=150)
        dest = f"assets/fig_p{page_num}_vector.jpg"
        shutil.move(output, dest)
        saved.append(dest)
    return saved
```

---

## Domain-Specific Logic（領域特定邏輯）

### 關鍵術語強制保護（`priority_terms.json`）

在任何 LLM 處理前，執行強制性字串替換。這是防止 AI 誤用相近詞彙的第一道防線：

```json
{
  "CRITICAL_SUBSTITUTIONS": {
    "輔料": "輔療",
    "Fulao": "輔療",
    "fu liao": "輔療",
    "輔療 (Fulao)": "輔療"
  },
  "CRITICAL_TERM_PROTECTION": [
    "輔療",
    "動物輔助治療",
    "綠色療癒",
    "五味屋",
    "友善雞蛋"
  ],
  "PROMPT_INJECTION": "以下術語在本文件中具有專門含義，禁止任何形式的同義替換或改寫：{terms}"
}
```

執行時機：
1. Docling 輸出 `raw_extracted.md` 後，在存入磁碟前執行替換
2. 每個 Gemini Prompt 的 system instruction 中注入 `PROMPT_INJECTION`
3. Gemma 4:E2B 的每次呼叫中也包含此術語清單

### 跨批次術語一致性（`global_session_memory.json`）

```json
{
  "pdf_id": "Psychology_Paper_05",
  "created_at": "2026-04-13T14:30:00",
  "locked_terms": {
    "Cognitive Load": "認知負荷",
    "Working Memory": "工作記憶",
    "Self-Determination Theory": "自我決定論"
  },
  "locked_at_chunk": {
    "認知負荷": 1,
    "工作記憶": 1,
    "自我決定論": 2
  }
}
```

機制：第一個 chunk 的 Agent Loop 完成後，Gemma 提取核心術語寫入此檔。後續每個 chunk 的 Gemini Prompt 開頭強制包含：`「【強制術語表】以下術語譯法已鎖定，不得更改：{locked_terms}」`

### OCR 品質門檻（`ocr_quality_gate.py`）

```python
CONFIDENCE_THRESHOLD = 0.80  # 低於此值觸發警告

def check_ocr_quality(pdf_path: str, page_num: int) -> float:
    """
    使用 pytesseract.image_to_data() 取得 per-word 信心分數。
    比 Docling 整頁判斷更細緻。
    返回: 該頁的平均信心分數 (0.0-1.0)
    """
    img = pdftoppm_page(pdf_path, page_num, dpi=200)  # 高解析度提升 OCR 準確率
    data = pytesseract.image_to_data(img, output_type=Output.DICT, lang='chi_tra+eng')
    scores = [c/100 for c in data['conf'] if c > 0]
    return sum(scores) / len(scores) if scores else 0.0
```

若任何頁面信心值 < 0.80：
- `scan_report.json` 記錄 `"low_confidence_pages": [3, 7, 12]`
- Dashboard 顯示黃色警告：`⚠️ [PDF名稱] 第 3, 7, 12 頁 OCR 信心值低，建議人工核對`
- 不阻塞流程，但在 `content.md` 對應段落插入 `> ⚠️ **[OCR品質警告]** 此段文字提取信心值低於 80%，請核對原始頁面`

### Green Care 接口（`triage.json`）

```json
{
  "complexity": "deep",
  "subject": "psychology",
  "gem_to_use": "psychology_expert",
  "has_statistics": true,
  "has_figures": true,
  "chunk_count": 6,
  "citation_style": "APA7",
  "language": "zh_tw",
  "green_care_potential": null,
  "notes": "含大量統計圖表"
}
```

`green_care_potential` 的判斷流程：
- Triage 時：永遠設為 `null`（Gemma 4:E2B 不做此判斷，避免跨領域誤判）
- Agent Loop 完成後：Gemini 在最後一輪自動評估（加入最後一個 chunk 的判斷 Prompt）
- 使用者可在 Dashboard 手動覆寫（Override 按鈕）

---

## Complete File & Folder Structure

```
open-claw-workspace/
│
├── core/                                ← 🔄 兩個 Skill 共用框架
│   ├── pipeline_base.py
│   ├── state_manager.py
│   ├── llm_client.py
│   ├── security_manager.py              ← 🆕 PDF Skill 貢獻
│   └── resume_manager.py               ← 🆕 PDF Skill 貢獻
│
└── skills/pdf-knowledge/
    │
    ├── config/
    │   ├── config.yaml
    │   ├── security_policy.yaml         ← 只有使用者可修改
    │   ├── whitelist.yaml               ← 使用者可編輯
    │   ├── selectors.yaml               ← 所有 Playwright DOM selectors
    │   ├── gem_configs.json
    │   ├── system_prompts.yaml
    │   └── priority_terms.json          ← 🆕 關鍵術語強制保護
    │
    ├── scripts/
    │   ├── main_app.py
    │   ├── inbox_watcher.py
    │   ├── queue_manager.py
    │   ├── pdf_diagnostic.py            ← 🆕 Phase 1a 輕量診斷（poppler-utils）
    │   ├── pdf_engine.py                ← Phase 1b 深度提取（Docling）
    │   ├── vector_chart_extractor.py    ← 🆕 Phase 1c 向量圖表補充（pdftoppm）
    │   ├── ocr_quality_gate.py          ← 🆕 OCR 信心分數門檻（pytesseract）
    │   ├── column_handler.py
    │   ├── image_extractor.py
    │   ├── reference_injector.py
    │   ├── git_manager.py
    │   ├── triage_agent.py
    │   ├── agent_loop.py
    │   ├── voyager_handler.py
    │   ├── whitelist_guard.py
    │   ├── chroma_manager.py
    │   ├── figure_describer.py
    │   ├── terminology_builder.py
    │   └── export_engine.py
    │
    ├── 01_Inbox/
    ├── 02_Processed/
    │   └── [PDF_ID]/
    │       ├── raw_extracted.md          ← IMMUTABLE
    │       ├── raw_extracted_chunk_{n}.md
    │       ├── triage.json
    │       ├── figure_list.md
    │       ├── refs.bib
    │       ├── scan_report.json          ← 含診斷結果、OCR 信心分數、向量圖表頁碼
    │       ├── global_session_memory.json ← 🆕 跨批次術語鎖定表
    │       └── assets/
    │
    ├── 03_Agent_Core/
    │   └── [PDF_ID]/
    │       ├── trace.md
    │       ├── resume_state.json
    │       ├── voyager_export.md
    │       ├── voyager_export.json
    │       ├── verification.json
    │       ├── security_audit.log
    │       └── verification/
    │           ├── round_{n}_sent.png
    │           ├── round_{n}_received.png
    │           └── source_snapshots/
    │
    ├── 05_Final_Knowledge/
    │   └── [PDF_ID]/
    │       ├── .git/
    │       ├── .gitattributes
    │       ├── content.md
    │       ├── figure_list.md           ← 含 VLM 描述 + 數據趨勢標籤
    │       ├── terminology.json         ← EN/繁中/Malay 三語
    │       ├── changes.log
    │       ├── verification.json
    │       └── assets/
    │
    ├── Error/
    ├── library/
    └── vector_db/
```

---

## Output Content Requirements

### content.md
- 完整文字保真（不摘要、不省略）
- H1/H2/H3 格式，單欄輸出
- LaTeX 公式 `$...$` / `$$...$$`（MathJax-ready，雙層保護：函數 + Prompt 禁令）
- 低信心 OCR 段落：`> ⚠️ **[OCR品質警告]** 此段信心值低，請核對原始頁面`
- 未核實 AI 內容：`> ⚠️ **[未核實]** 請人工確認`

### figure_list.md — 含數據趨勢標籤（新增）

```markdown
| 檔案名稱 | 頁碼 | 原始 Caption | VLM 描述（學科感知）| 數據趨勢標籤 | 來源 |
| :--- | :---: | :--- | :--- | :---: | :---: |
| fig_p3_1.png | 3 | Fig.1: Scatter Plot | 散佈圖，實驗組(n=60) vs 對照組，Pearson r=0.72，p<0.01 | Positive_Correlation | [P] |
| fig_p5_2.png | 5 | Fig.2: Time Series | 四波段縱向追蹤，T1→T4 整體下降趨勢，T3 出現反彈 | Decreasing_Trend | [P] |
| fig_p7_1_vector.jpg | 7 | Fig.3: Bar Chart | 向量圖光柵化。六組長條圖，Effect Size 從大到小排列 | Comparative | [P] |
```

數據趨勢標籤詞彙表（Gemma 4:E2B 從此清單選擇）：
`Positive_Correlation` / `Negative_Correlation` / `No_Correlation` / `Increasing_Trend` / `Decreasing_Trend` / `Cyclical` / `Comparative` / `Distribution` / `Network` / `Process_Flow`

這使 Dashboard 的「搜尋正相關圖表」跨文件篩選成為可能。

### Anki 卡片 Schema

| 欄位 | 來源 | 處理 |
| :--- | :--- | :--- |
| Front（正面）| `terminology.json` → `term` | 顯示：EN / 繁中 / Malay 三語術語 |
| Back（背面）| `definition` + 原始 PDF 段落 | 自動從 `content.md` 擷取含該詞的原始句子（上下文各一句）|
| Source（來源）| `pdf_id` + 術語首次出現頁碼 | 標注原始文獻出處 |
| Domain | `triage.json` → `subject` | 按學科分組 Anki Deck |

### Marp PPT Schema

- **Slide 1**: `H1`（PDF 標題）+ `refs.bib` 核心作者
- **Slide 2**: Agent Loop 完成後由 Gemini 提取的「3 Key Learning Points」（`content.md` 後處理，非 Triage 生成）
- **Content Slides**: 每個 `H2` 強制開始新分頁（`---`）；`H2` 下有圖片時自動置入左側 50% 寬度
- **觸發**: `subject == "curriculum"` 或 Dashboard 手動請求

---

## Hardware Defence Metrics

> [!WARNING]
> | 等級 | 條件 | 行為 |
> | :--- | :--- | :--- |
> | ⚠️ Warning | 可用 RAM < 2 GB | 暫停佇列 |
> | 🚨 Critical | 可用 RAM < 500 MB | 中止 + resume_state.json + PDF → Error/ |
> | 🌡️ Thermal | CPU > 90°C | 暫停 5 分鐘 |
> | 🔋 Battery | < 15% 未接電 | Dashboard 警告（不強制中止）|
> | 💾 Disk | < 500 MB | 拒絕新任務 |
> | ⏱️ Thinking | > 8 分鐘 | 截圖 + 人工介入提示 |
> | 🔄 Loop | rounds > 10 | 暫停（可延伸）|
> | 🔤 OCR | 信心值 < 0.80 | 黃色警告，繼續 |
> | 🔡 Font | 字型未嵌入 | scan_report 警告，建議光柵化 |

---

## V2.1 AI Collaboration Protocol

任何 AI 修改此 Repository 必須：
1. 每次成功 deploy 後 `git commit`
2. 架構改動後依序更新六份 Meta 文件
3. **永遠不修改** `02_Processed/[PDF_ID]/raw_extracted*.md`
4. **永遠不引入** `google.generativeai` SDK
5. **永遠不修改** `config/security_policy.yaml`（只有使用者可改）
6. 所有 Playwright selector 寫入 `config/selectors.yaml`
7. Voyager 導出只在整個 PDF 的 Agent Loop 全部完成後觸發一次
8. 中斷前必須寫 `resume_state.json`
9. `priority_terms.json` 的 CRITICAL 術語在每次 LLM 呼叫前強制執行
10. `global_session_memory.json` 第一個 chunk 完成後立即寫入，後續 chunk 必須讀取
