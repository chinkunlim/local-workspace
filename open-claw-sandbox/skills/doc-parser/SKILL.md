---
name: doc-parser
description: Process scanned or structured PDFs using Docling, OCR validation, and VLM extraction to synthesize them into unified markdown study guides.
metadata:
  {
    "openclaw":
      {
        "emoji": "📄"
      }
  }
---

# Doc Parser Skill

> **Pipeline**: PDF → Diagnose → Extract → VLM Vision

## Quick Start

```bash
# 1. 放 PDF 進 Inbox（Universal Drop Zone）
cp textbook.pdf data/raw/AI_Papers/

# 2. 執行流水線 (Headless Batch Mode)
python3 skills/doc-parser/scripts/run_all.py --process-all

# 3. 查看進度
cat data/doc-parser/state/checklist.md
```

## 核心解析機制 (V2.0 Antigravity)

| Phase | 腳本 | 功能 |
|:---:|:---|:---|
| P0a | `p00a_diagnostic.py` | 輕量診斷（頁數、文字密度、掃描判斷） |
| P1a | `p01a_engine.py` | Docling 深度提取 → `raw_extracted.md` (IMMUTABLE) |
| P1b | `p01b_vector_charts.py` | 向量圖表光柵化 (pdftoppm) |
| P1c | `p01c_ocr_gate.py` | OCR 品質評估（掃描件才觸發） |
| P1d | `p01d_vlm_vision.py` | **VLM 圖像自動描述**：動態解析 `figure_list.md`，自動鎖定 `待 VLM 描述` 的項目並調用 Vision 模型處理。具備容錯機制（圖片遺失優雅降級），最後進行 Atomic Markdown 寫回。強制 `temperature: 0` 防止幻覺。 |

## 常用指令

```bash
# 只處理特定科目的 PDF
python3 skills/doc-parser/scripts/run_all.py --subject AI_Papers

# 背景批次執行 (自動處理全部)
python3 skills/doc-parser/scripts/run_all.py --process-all

# 輸出 JSON 格式日誌 (Headless Telemetry)
python3 skills/doc-parser/scripts/run_all.py --process-all --log-json

# 互動切換模型
python3 core/cli_config_wizard.py --skill doc-parser
```

## 目錄說明

| 路徑 | 說明 |
|:---|:---|
| `input/<subject>/` | PDF 入匣，放新文件至此 |
| `output/01_Processed/<subject>/<id>/` | Docling 原始提取（**勿修改**）|
| `state/checklist.md` | 自動生成的進度追蹤表 |

## 設定檔位置

- **主設定**: `config/config.yaml` — 模型選擇、路徑、OCR 閾值、分塊大小
- **術語保護**: `config/priority_terms.json` — 跨 skill 術語清單
- **詳細文件**: `docs/ARCHITECTURE.md`
