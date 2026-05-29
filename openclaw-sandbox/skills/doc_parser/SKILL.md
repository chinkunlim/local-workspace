---
name: doc_parser
description: Process scanned or structured PDFs using Docling, OCR validation, and VLM extraction to synthesize them into unified Obsidian-ready markdown study notes.
metadata:
  {
    "openclaw":
      {
        "emoji": "📄"
      }
  }
state_tracking:
  phases: ["p0c", "p0b", "p0a", "p1a", "p1b_s", "p1b", "p1c", "p1d"]
  labels:
    p0c: "P0c (MarkItDown 轉換)"
    p0b: "P0b (圖片提取)"
    p0a: "P0a (診斷)"
    p1a: "P1a (提取)"
    p1b_s: "P1b-S (文字淨化)"
    p1b: "P1b (向量圖)"
    p1c: "P1c (OCR評估)"
    p1d: "P1d (VLM視覺)"
io_contracts:
  consumes: 
    - "application/pdf"
    - "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    - "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    - "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  produces: 
    - "text/markdown"
---

# Doc Parser Skill

> **Pipeline**: PDF → Diagnose → Extract → OCR Gate → VLM Vision → Synthesis

## Quick Start

```bash
# 1. Drop PDF files into the Universal Inbox
cp textbook.pdf data/raw/<SubjectName>/

# 2. Run in headless batch mode
python3 skills/doc_parser/scripts/run_all.py --process-all

# 3. Check pipeline progress
cat data/doc_parser/state/checklist.md
```

## Core Extraction Architecture (V2.0 Antigravity)

| Phase | Script | Function |
|:---:|:---|:---|
| P00a | `p00a_diagnostic.py` | Security check + PDF metadata extraction |
| P00b | `p00b_png_pipeline.py` | Tesseract OCR and layout extraction for direct PNG inputs |
| P01a | `p01a_engine.py` | Primary Docling extraction → `raw_extracted.md` |
| P01b | `p01b_vector_charts.py` | Vector diagram detection and captioning |
| P01c | `p01c_ocr_gate.py` | Adaptive OCR decision (triggers only when Docling coverage is insufficient) |
| P01d | `p01d_vlm_vision.py` | Figure / image analysis via VLM (vision language model) |
| Handoff | (Autonomous) | The RouterAgent automatically forwards the extracted content to the `proofreader` skill for AI verification and dashboard review. |

## Common Commands

```bash
# Run full pipeline on all pending PDFs
python3 skills/doc_parser/scripts/run_all.py --process-all

# Run from a specific phase
python3 skills/doc_parser/scripts/run_all.py --from 2

# Force re-run on all files
python3 skills/doc_parser/scripts/run_all.py --process-all --force

# Process a single subject
python3 skills/doc_parser/scripts/run_all.py --subject <SubjectName>
```

## Security Contract

- Source PDF files are **immutable** — they are read-only and never modified or moved.
- All extracted content is written via `AtomicWriter` to guarantee crash-safe output.
- The Security Manager runs a path-traversal check on every filename before any processing begins.

## Global Standards

- **Zero Temperature**: `config.yaml` enforces `temperature: 0` to guarantee deterministic, hallucination-free outputs.
- **Headless CLI**: Supports `--process-all`, `--from`, `--force`, `--resume`, `--log-json` for full CI/CD compatibility.
- **Preflight Check**: Validates all dependencies and config on every run before processing begins.
- **Checkpoint Resume**: All phase completions are saved to `state/`; use `--resume` to continue after an interruption.
- macOS native notifications (`osascript`) and graceful `KeyboardInterrupt` handling with checkpoint save.
