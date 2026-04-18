# Open Claw — PDF Knowledge Skill Architecture

> Version: V3.0 | Last Updated: 2026-04-16

## 1. 概覽

PDF Knowledge Skill 是 Open Claw 的 PDF 知識庫建立流水線，負責將 PDF 文件自動化提取、分析、VLM 圖像解析，最終合成為結構化的 Markdown 知識庫。

```
01_Inbox/<subject>/<pdf_name>.pdf
          │
          ▼ P0a: 輕量診斷 (頁數、文字密度、掃描判斷)
          │
          ▼ P1a: Docling 深度提取 → raw_extracted.md (IMMUTABLE)
          │
          ├──▶ P1b: 向量圖表光柵化 (pdftoppm)
          │
          └──▶ P1c: OCR 品質評估 (掃描件才觸發)
          │
          ▼ P1d: VLM 視覺圖表解析 (figure_list.md 更新)
          │
          ▼ P3: Map-Reduce 知識合成 → content.md
          │
          ▼
05_Final_Knowledge/<subject>/<pdf_id>/content.md
```

---

## 2. 目錄結構

```
skills/pdf-knowledge/
├── SKILL.md                       # AgentSkill registration + Quick-start 指南
├── config/
│   ├── config.yaml                # 路徑、模型、概念限定 (skill-specific only)
│   ├── prompt.md                  # Phase 1d/2b LLM 指令模板 (零硬編碼)
│   ├── priority_terms.json        # 跨 skill 術語保護清單
│   ├── security_policy.yaml       # PDF 安全掃描規則
│   └── selectors.yaml             # 資料來源選擇器
├── docs/
│   ├── ARCHITECTURE.md            # 本文件
│   ├── DECISIONS.md               # 技術決策日誌
│   └── CLAUDE.md                  # AI 協作上下文
└── scripts/
    ├── run_all.py                  # QueueManager — 佇列式六階段執行器
    └── phases/
        ├── p01a_diagnostic.py     # Phase 0a: 軽量 PDF 診斷
        ├── p01b_engine.py         # Phase 1a: Docling 深度提取
        ├── p01c_vector_charts.py  # Phase 1b: 向量圖表補充 (300 DPI)
        ├── p01d_ocr_gate.py       # Phase 1c: OCR 品質評估
        ├── p02a_vlm_vision.py     # Phase 1d: VLM 圖像解析
        └── p02b_synthesis.py      # Phase 3: Map-Reduce 知識合成
```

---

## 3. Subject-Based 階層架構

pdf-knowledge 的 Inbox 和 Output 均按科目分層管理：

```
data/pdf-knowledge/
├── input/
│   └── 01_Inbox/
│       ├── AI_Papers/          ← subject 資料夾
│       │   ├── attention.pdf
│       │   └── bert.pdf
│       └── Physics/
│           └── quantum.pdf
└── output/
    ├── 01_processed/<subject>/<pdf_id>/  # raw_extracted.md, images/
    ├── 02_highlighted/<subject>/<pdf_id>/ # highlighted.md
    ├── 03_synthesis/<subject>/<pdf_id>/ # content.md
    ├── error/<subject>/<pdf_id>/        # failed processing
    ├── vector_db/                         # ChromaDB 向量資料庫
    └── library/                           # 文件彙整
```

---

## 4. 核心架構原則

### 4.1 繼承關係

```python
class Phase1bPDFEngine(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="phase1b",
            phase_name="Docling 深度提取",
            skill_name="pdf-knowledge"
        )
        # self.dirs["processed"] → data/pdf-knowledge/output/01_processed
        # self.dirs["final"]     → data/pdf-knowledge/output/03_synthesis
```

### 4.2 路徑解析 (Config-Driven)

```yaml
# skills/pdf-knowledge/config/config.yaml
paths:
  input:  "input/01_Inbox"
  output: "output"
  state:  "state"
  logs:   "logs"
  phases:
    inbox:       "input/01_Inbox"
    processed:   "output/01_processed"
    highlighted: "output/02_highlighted"
    synthesis:   "output/03_synthesis"
    error:       "output/error"
    vector_db:   "output/vector_db"
    library:     "output/library"
```

### 4.3 狀態追蹤

- `core.StateManager(skill_name="pdf-knowledge")` 管理六個 Phase 的進度
- Phase 集合：`["p0a", "p1a", "p1b", "p1c", "p1d", "p3"]`
- `data/pdf-knowledge/state/checklist.md` 追蹤每份 PDF 的處理狀態

### 4.4 IMMUTABLE 原則

`02_Processed/<subject>/<pdf_id>/raw_extracted.md` 是 Docling 的原始輸出，永不覆寫。後續所有 AI 加工結果寫入 `05_Final_Knowledge/`，確保可回溯性。

### 4.5 Content-Loss Guard

P3 合成後自動計算壓縮率。為反映 PDF 知識庫體積文字天然深度合成的特性，門檩已調整為 `≥ 1%`，防止 LLM 偷懶截斷。

### 4.6 全局設定層級

```
core/config/global.yaml        ← 硬體閾値 + Ollama runtime
    ↓ deep-merge
skills/pdf-knowledge/config/config.yaml  ← skill-specific 設定（如需可覆寫全局層）
```

`ConfigManager._deep_merge()` 確保 skill 設定覆盓全局預設。

### 4.7 LLM 指令零硬編碼

所有 LLM prompt 存放於 `config/prompt.md`，由 `PipelineBase.get_prompt(section_title)` 按 `## 小標題` 解析。修改 prompt **不需動到任何 Python 程式碼**。

---

## 5. QueueManager 佇列機制

`run_all.py` 的 `QueueManager` 繼承 `PipelineBase`，負責：

1. 遞迴掃描 `01_Inbox/<subject>/` 發現未處理 PDF
2. MD5 去重（避免重複處理相同檔案）
3. `ModelMutex` 確保 Docling 不被並發占用
4. 每個 Phase 結束後寫入 `StateManager.update_task()`，更新 `checklist.md`
5. 支援 `--interactive` 模式在 P1d 後暫停等待人工確認圖表

---

## 6. 與 Core 的依賴關係

| Core 模組 | PDF Knowledge 用途 |
|:---|:---|
| `PipelineBase` | 所有 Phase 類別的基底 |
| `ConfigManager` | 載入 `global.yaml` + `config.yaml` 分層合併 |
| `StateManager(skill_name="pdf-knowledge")` | P0a-P3 進度追蹤 |
| `PathBuilder` | 從 config.yaml `paths.phases` 解析目錄 |
| `OllamaClient` | P1d (llama3.2-vision VLM) 和 P3 (qwen2.5:14b synthesis) LLM 推論 |
| `SecurityManager` | P0a 前的 PDF 安全掃描 |
| `GlossaryManager` | 從 voice-memo 同步術語至 priority_terms.json |
| `DiffEngine` | raw_extracted ↔ content.md 差異檢視 |
| `text_utils.smart_split` | P3 Map-Reduce 分塊 |
| `SystemInboxDaemon` | 監聴 `01_Inbox/` 新增 PDF |

---

## 7. 執行方式

```bash
# 處理所有 Inbox 中的 PDF
cd open-claw-sandbox
python3 skills/pdf-knowledge/scripts/run_all.py

# 只處理特定科目的 PDF
python3 skills/pdf-knowledge/scripts/run_all.py --subject AI_Papers

# 互動模式（P1d 後暫停等待圖表確認）
python3 skills/pdf-knowledge/scripts/run_all.py --interactive

# 切換 LLM 模型設定
python3 core/cli_config_wizard.py --skill pdf-knowledge
```

---

## 8. 與 Voice Memo 的功能對齊

| 功能 | Voice Memo | PDF Knowledge |
|:---|:---:|:---:|
| Subject-based 分層 | ✅ | ✅ |
| StateManager 進度追蹤 | ✅ P1-P5 | ✅ P0a-P3 |
| Config-driven 路徑 | ✅ | ✅ |
| InboxDaemon 監聽 | ✅ | ✅ |
| DiffEngine 比對 | ✅ P1↔P2 | ✅ raw↔final |
| Checkpoint Resume | ✅ | ✅ |
| IMMUTABLE 原始輸出 | ✅ P1 | ✅ P1a |
| Content-Loss Guard | — | ✅ P3 |
| VLM 圖像解析 | — | ✅ P1d |
| OCR 品質門控 | — | ✅ P1c |
