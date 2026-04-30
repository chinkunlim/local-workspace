---
name: audio-transcriber
description: End-to-end voice processing pipeline. Converts .m4a audio into polished, MLX-Whisper transcribed Obsidian-ready study notes.
metadata:
  {
    "openclaw":
      {
        "emoji": "🎙️"
      }
  }
---

# Audio Transcriber Skill

> **Pipeline**: M4A → Glossary → Transcription → Proofread → Merge

## Quick Start

```bash
# 1. Drop audio files into the Universal Inbox
cp lecture.m4a data/raw/<SubjectName>/

# 2. Run in headless batch mode
python3 skills/audio-transcriber/scripts/run_all.py --process-all

# 3. Check pipeline progress
cat data/audio-transcriber/state/checklist.md
```

## Anti-Hallucination Defense Architecture (V8.1)

| Phase | Script | Function |
|:---:|:---|:---|
| P0 | `p00_glossary.py` | Glossary initialisation — prevents LLM from fabricating domain-specific terms |
| P1 | `p01_transcribe.py` | High-fidelity transcription via MLX-Whisper. **VAD silence-trimming guard**: uses `pydub.silence` to pre-strip noise. If `silence_ratio > max_removal_ratio` (default: 0.90), automatically falls back to the raw audio to prevent over-trimming. Includes multi-clip majority-vote language detection. |
| P2 | `p02_proofread.py` | LLM-assisted intelligent proofreading with glossary term protection |
| P3 | `p03_merge.py` | Cross-segment consolidation and refinement |

## Common Commands

```bash
# Run full pipeline on all pending files
python3 skills/audio-transcriber/scripts/run_all.py --process-all

# Run from a specific phase
python3 skills/audio-transcriber/scripts/run_all.py --from 2

# Force re-run on all files
python3 skills/audio-transcriber/scripts/run_all.py --process-all --force

# Regenerate glossary only
python3 skills/audio-transcriber/scripts/run_all.py --glossary

# Process a single subject
python3 skills/audio-transcriber/scripts/run_all.py --subject <SubjectName>
```

## Global Standards

- **Zero Temperature**: `config.yaml` enforces `temperature: 0` to guarantee deterministic, hallucination-free outputs.
- **Headless CLI**: Supports `--process-all`, `--from`, `--force`, `--resume`, `--log-json` for full CI/CD compatibility.
- **Preflight Check**: Validates all dependencies and config on every run before processing begins.
- **Checkpoint Resume**: All phase completions are saved to `state/`; use `--resume` to continue after an interruption.
- macOS native notifications (`osascript`) and graceful `KeyboardInterrupt` handling with checkpoint save.
