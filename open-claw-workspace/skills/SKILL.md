---
skills:
  - name: voice-memo
    description: Five-phase academic voice-memo processing pipeline. Converts raw lecture recordings (.m4a) into polished Notion-ready study notes via transcription, proofreading, merging, highlighting, and synthesis.
  - name: pdf-knowledge
    description: Local-first academic PDF knowledge extraction and synthesis system. Ingests PDFs (psychology, IT, curriculum design) and outputs editable, version-controlled, citation-verified Markdown knowledge base.
---

# OpenClaw Skills Registry

Two active skills are available. Read the intent and dispatch accordingly.

---

## 🎙️ Skill 1 — Voice Memo Pipeline

> Full details: `skills/voice-memo/SKILL.md`

**Trigger phrases**: 語音轉錄, 校對逐字稿, 合併段落, 標記重點, 生成 Notion 筆記, "transcribe audio", "run pipeline", "proofread", "synthesize notes"

### Quick Dispatch Table

| User Intent | Command |
| :--- | :--- |
| *「設定模型」* / *"Configure models"* | `python3 skills/voice-memo/scripts/setup_wizard.py` |
| *「完整跑一次」* / *"Run the full pipeline"* | `python3 skills/voice-memo/scripts/run_all.py` |
| *「單獨跑某科目」* / *"Only process [subject]"* | `python3 skills/voice-memo/scripts/run_all.py --subject <科目>` |
| *「互動模式」* / *"Run with review pauses"* | `python3 skills/voice-memo/scripts/run_all.py --interactive` |
| *「從第N步繼續」* / *"Resume from Phase N"* | `python3 skills/voice-memo/scripts/run_all.py --from N` |
| *「全部重跑」* / *"Force reprocess"* | `python3 skills/voice-memo/scripts/run_all.py --force` |
| *「轉錄相音」* / *"Transcribe"* | `python3 skills/voice-memo/scripts/transcribe_tool.py` |
| *「校對逐字稿」* / *"Proofread"* | `python3 skills/voice-memo/scripts/proofread_tool.py` |
| *「合併段落」* / *"Merge"* | `python3 skills/voice-memo/scripts/merge_tool.py` |
| *「標記重點」* / *"Highlight"* | `python3 skills/voice-memo/scripts/highlight_tool.py` |
| *「生成 Notion 筆記」* / *"Synthesize"* | `python3 skills/voice-memo/scripts/notion_synthesis.py` |

**All commands must be run from workspace root**:
```
cd /Users/limchinkun/Desktop/local-workspace/open-claw-workspace
```

---

## 📚 Skill 2 — PDF Knowledge Extraction

> Full details: `skills/pdf-knowledge/SKILL.md`

**Trigger phrases**: PDF, 知識提取, 論文, 學術文件, 診斷 PDF, 處理 PDF, "extract PDF", "run PDF pipeline", "OCR", "知識庫", "figure list", "Docling"

### Quick Dispatch Table

| User Intent | Command |
| :--- | :--- |
| *「開啟 PDF 儀表板」* / *"Open dashboard"* | `python3 skills/pdf-knowledge/scripts/main_app.py` → `http://127.0.0.1:5001` |
| *「處理所有 PDF」* / *"Process all PDFs"* | `python3 skills/pdf-knowledge/scripts/queue_manager.py --process-all` |
| *「診斷這個 PDF」* / *"Diagnose PDF"* | `python3 skills/pdf-knowledge/scripts/pdf_diagnostic.py <路徑>` |
| *「提取 PDF 內容」* / *"Extract PDF"* | `python3 skills/pdf-knowledge/scripts/pdf_engine.py <路徑>` |
| *「補充向量圖表」* / *"Extract vector charts"* | `python3 skills/pdf-knowledge/scripts/vector_chart_extractor.py <路徑> --from-report` |
| *「評估 OCR 品質」* / *"Assess OCR quality"* | `python3 skills/pdf-knowledge/scripts/ocr_quality_gate.py <路徑>` |
| *「有哪些未完成的 PDF」* | `curl http://127.0.0.1:5001/resume` |
| *「監控 Inbox」* / *"Watch inbox"* | `python3 skills/pdf-knowledge/scripts/inbox_watcher.py` |

**Inbox directory**: `data/pdf-knowledge/01_Inbox/` — 將 PDF 放入此資料夾觸發處理

---

## Dispatcher Notes

- **Ambiguous intent**: If the user mentions both voice and PDF, ask for clarification.
- **Skill independence**: Both skills share the same `core/` framework but have completely separate data directories (`data/voice-memo/` vs `data/pdf-knowledge/`).
- **Security**: PDF skill's Playwright operations are bounded by `skills/pdf-knowledge/config/security_policy.yaml`. Never modify this file.
- **Core framework**: Located at `core/` in workspace root. Shared by both skills.
