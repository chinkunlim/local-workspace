---
name: voice-memo
description: >
  Five-phase academic voice-memo processing pipeline.
  Converts raw lecture recordings (.m4a) into polished Notion-ready study notes
  via sequential transcription, proofreading, merging, highlighting, and synthesis.
---

# Voice Memo Pipeline (V5.0 — Five-Phase Edition)

This skill provides full orchestration of the voice-memo processing pipeline.
The pipeline runs five discrete, sequential phases — each reading from the previous
phase's dedicated output directory and writing to its own.

**Data Lineage**:
`input/raw_data/` → `output/01_transcript/` → `output/02_proofread/` → `output/03_merged/` → `output/04_highlighted/` → `output/05_notion_synthesis/`

**State / Logs**:
`state/.pipeline_state.json` · `state/checklist.md` · `logs/system.log`

## Capabilities / Tools

All scripts must be invoked using their **absolute paths**.
**Workspace root**: `/Users/limchinkun/Desktop/local-workspace/open-claw-workspace`

---

### ⚙️ Quick Setup (配置精靈)
- **Script:** `skills/voice-memo/scripts/setup_wizard.py`
- **Action:** Interactive CLI wizard for setting up model selections in config.json without writing JSON manually.

```
cd /Users/limchinkun/Desktop/local-workspace/open-claw-workspace && python3 skills/voice-memo/scripts/setup_wizard.py
```

---

### 🚀 RECOMMENDED: Full Pipeline (Orchestrator)
- **Script:** `skills/voice-memo/scripts/run_all.py`
- **Action:** Executes all five phases in sequence. Automatically skips files already marked ✅ in `checklist.md`. Supports human-in-the-loop review pauses.

```
# Run all phases end-to-end (skips completed files)
cd /Users/limchinkun/Desktop/local-workspace/open-claw-workspace && python3 skills/voice-memo/scripts/run_all.py

# Run for a specific subject only (Only process files under that directory)
python3 skills/voice-memo/scripts/run_all.py --subject 生理心理學

# Pause for human review between phases
python3 skills/voice-memo/scripts/run_all.py --interactive

# Resume from a specific phase (e.g. after manually editing 02_proofread/)
python3 skills/voice-memo/scripts/run_all.py --from 3

# Force-reprocess ALL files from scratch
python3 skills/voice-memo/scripts/run_all.py --force
```

---

### 🎙️ Phase 1 — Transcription (轉錄)
- **Script:** `skills/voice-memo/scripts/transcribe_tool.py`
- **Action:** Converts `.m4a` audio into two Markdown files per recording:
  - `<name>.md` — pure text (feeds Phase 2)
  - `<name>_timestamped.md` — time-coded (human reference)
- **Engine:** Selectable via `config.json → phase1.active_profile` (`faster-whisper` CPU or `mlx-whisper` Apple Silicon MPS).

```
cd /Users/limchinkun/Desktop/local-workspace/open-claw-workspace && python3 skills/voice-memo/scripts/transcribe_tool.py
python3 skills/voice-memo/scripts/transcribe_tool.py --force   # re-transcribe all
```

---

### 🧠 Phase 2 — Proofreading (校對)
- **Script:** `skills/voice-memo/scripts/proofread_tool.py`
- **Action:** Fixes transcription errors 1-to-1 against each segment file using a local LLM (default: `gemma3:12b`) and optional co-located PDF slides. **Does not merge or restructure** — pure correction only.

```
cd /Users/limchinkun/Desktop/local-workspace/open-claw-workspace && python3 skills/voice-memo/scripts/proofread_tool.py
python3 skills/voice-memo/scripts/proofread_tool.py --force
```

---

### 🔗 Phase 3 — Merge & Speaker Diarization (合併與對話編排)
- **Script:** `skills/voice-memo/scripts/merge_tool.py`
- **Action:** Groups segmented lecture files (e.g. `L01-1.md`, `L01-2.md`) and merges them into `L01.md`. Applies LLM-based paragraph breaking and speaker labelling:
  - Standard mode: `教授：` / `學生：`
  - `助人歷程` subject: `同學A：` / `同學B：` / `助人者 (同學A)：` / `個案 (同學B)：`

```
cd /Users/limchinkun/Desktop/local-workspace/open-claw-workspace && python3 skills/voice-memo/scripts/merge_tool.py
python3 skills/voice-memo/scripts/merge_tool.py --force
```

---

### 🖊️ Phase 4 — Highlight & Emphasis (重點標記)
- **Script:** `skills/voice-memo/scripts/highlight_tool.py`
- **Action:** Applies Markdown emphasis (`**bold**`, `==highlight==`, `*italic*`) to key concepts. **Anti-tampering guard**: if LLM output is >5 % shorter than input, the original chunk is preserved automatically.

```
cd /Users/limchinkun/Desktop/local-workspace/open-claw-workspace && python3 skills/voice-memo/scripts/highlight_tool.py
python3 skills/voice-memo/scripts/highlight_tool.py --force
```

---

### ✨ Phase 5 — Notion Synthesis (知識合成)
- **Script:** `skills/voice-memo/scripts/notion_synthesis.py`
- **Action:** Transforms highlighted transcripts into structured academic notes:
  🎓 Key Points · 📝 Cornell Table · 🧠 Mermaid Mind Map · 💡 QEC · 👶 Feynman · 🏷️ Hashtags

```
cd /Users/limchinkun/Desktop/local-workspace/open-claw-workspace && python3 skills/voice-memo/scripts/notion_synthesis.py
python3 skills/voice-memo/scripts/notion_synthesis.py --force
```

---

## User Intent & Invocation

When the user sends a request via Telegram or Chat, map their intent to the command below:

| User Intent | Action |
| :--- | :--- |
| *「設定模型」* / *"Configure models"* | `setup_wizard.py` |
| *「完整跑一次」* / *"Run the full pipeline"* | `run_all.py` |
| *「單獨跑生理心理學」* / *"Only process psychology"* | `run_all.py --subject 生理心理學` |
| *「互動模式跑」* / *"Run with review pauses"* | `run_all.py --interactive` |
| *「從第3步繼續」* / *"Resume from Phase 3"* | `run_all.py --from 3` |
| *「全部重跑」* / *"Force reprocess everything"* | `run_all.py --force` |
| *「轉錄語音」* / *"Transcribe audio"* | `transcribe_tool.py --subject 生理心理學` |
| *「校對逐字稿」* / *"Proofread transcripts"* | `proofread_tool.py --subject 生理心理學` |
| *「合併段落」* / *"Merge segments"* | `merge_tool.py --subject 生理心理學` |
| *「標記重點」* / *"Highlight key points"* | `highlight_tool.py --subject 生理心理學` |
| *「生成 Notion 筆記」* / *"Create Notion notes"* | `notion_synthesis.py --subject 生理心理學` |

## Notes

- **Prompts**: Loaded from `skills/voice-memo/scripts/prompt.md`. Each phase has its own `## Phase N:` section. Edit that file to tune LLM behaviour without touching Python code.
- **Models & Parameters**: Configured in `voice-memo/config.json`. Each phase has its own `phaseN` key with `active_profile` and `subject_overrides` switching support.
- **Command Line Overrides**: ALL script actions accept `--subject <subj_name>` to restrict execution to that folder.
- **State Tracking**: All progress is persisted in `data/voice-memo/state/checklist.md` (5 columns: P1–P5). Interrupted runs resume automatically from where they stopped.
- **Canonical Layout**: Legacy phase folders remain as compatibility aliases, but new work should target `input/`, `output/`, `state/`, and `logs/`.
- **Hardware Safety**: Base classes monitor RAM, disk, battery, and temperature. Critical thresholds trigger automatic shutdown to protect hardware.
- **Progress Display**: All scripts show `[X/Y]` file counters in terminal so you can report progress to the user.
