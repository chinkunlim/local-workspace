---
name: pdf-knowledge
description: Process scanned or structured PDFs using Docling, OCR validation, and VLM extraction to synthesize them into unified markdown study guides.
metadata:
  {
    "openclaw":
      {
        "emoji": "📄"
      }
  }
---

# PDF Knowledge Skill

> **Pipeline**: PDF → Diagnose → Extract → VLM Vision → Synthesize → Markdown KB

## Quick Start

```bash
# 1. 放 PDF 進 Inbox（按科目分類）
cp textbook.pdf data/pdf-knowledge/input/01_Inbox/AI_Papers/

# 2. 執行流水線
python3 skills/pdf-knowledge/scripts/run_all.py

# 3. 查看進度
cat data/pdf-knowledge/state/checklist.md

# 4. Review Board（raw vs final 差異比對）
open http://localhost:5001
```

## 六個 Phase

| Phase | 腳本 | 功能 |
|:---:|:---|:---|
| P1a | `p01a_diagnostic.py` | 輕量診斷（頁數、文字密度、掃描判斷） |
| P1b | `p01b_engine.py` | Docling 深度提取 → raw_extracted.md |
| P1c | `p01c_vector_charts.py` | 向量圖表光柵化 (pdftoppm) |
| P1d | `p01d_ocr_gate.py` | OCR 品質評估（掃描件才觸發） |
| P2a | `p02a_vlm_vision.py` | VLM 圖像自動描述 |
| P2b | `p02b_synthesis.py` | Map-Reduce 知識合成 → content.md |

## 常用指令

```bash
# 只處理特定科目的 PDF
python3 skills/pdf-knowledge/scripts/run_all.py --subject AI_Papers

# 互動模式（P2a 後暫停，可人工確認圖表）
python3 skills/pdf-knowledge/scripts/run_all.py --interactive

# 互動切換模型
python3 core/cli_config_wizard.py --skill pdf-knowledge
```

## 目錄說明

| 路徑 | 說明 |
|:---|:---|
| `input/01_Inbox/<subject>/` | PDF 入匣，放新文件至此 |
| `output/02_Processed/<subject>/<id>/` | Docling 原始提取（**勿修改**）|
| `output/05_Final_Knowledge/<subject>/<id>/` | 最終知識庫 Markdown |
| `state/checklist.md` | 自動生成的進度追蹤表 |

## 設定檔位置

- **主設定**: `config/config.yaml` — 模型選擇、路徑、OCR 閾值、分塊大小
- **術語保護**: `config/priority_terms.json` — 跨 skill 術語清單
- **詳細文件**: `docs/ARCHITECTURE.md`
