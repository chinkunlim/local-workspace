---
name: audio_transcriber
description: End-to-end voice processing pipeline. Converts .m4a audio into polished, MLX-Whisper transcribed Obsidian-ready study notes.
metadata:
  {
    "openclaw":
      {
        "emoji": "🎙️"
      }
  }
state_tracking:
  phases: ["p1", "p2", "p3"]
  labels:
    p1: "P1 (轉錄)"
    p2: "P2 (校對)"
    p3: "P3 (合併)"
io_contracts:
  consumes:
    - "audio/mp4"
    - "audio/mpeg"
    - "audio/wav"
  produces:
    - "text/markdown"
---

# Audio Transcriber Skill

> **Pipeline**: M4A → Glossary → Transcription → Proofread → Merge

## Quick Start

```bash
# 1. Drop audio files into the Universal Inbox
cp lecture.m4a data/raw/<SubjectName>/

# 2. Run in headless batch mode
python3 skills/audio_transcriber/scripts/run_all.py --process-all

# 3. Check pipeline progress
cat data/audio_transcriber/state/checklist.md
```

## Anti-Hallucination Defense Architecture (V8.1)

| Phase | Script | Function |
|:---:|:---|:---|
| P0 | `p00_glossary.py` | Glossary initialisation — prevents LLM from fabricating domain-specific terms |
| P1 | `p01_transcribe.py` | High-fidelity transcription via MLX-Whisper. **VAD silence-trimming guard**: uses `pydub.silence` to pre-strip noise (Requires `ffmpeg` installed on system to decode audio files). If `silence_ratio > max_removal_ratio` (default: 0.90) or ffmpeg decoding fails, automatically falls back to the raw audio to prevent over-trimming. Includes multi-clip majority-vote language detection. |
| P2 | `p02_glossary_apply.py` | Automatically applies glossary constraints to the raw transcript to ensure terminology accuracy before proofreading. |
| P3 | `p03_merge.py` | Cross-segment consolidation and refinement. |
| Handoff | (Autonomous) | The RouterAgent automatically forwards the merged transcript to the `proofreader` skill for AI verification against reference material and dashboard review. |

## Common Commands

```bash
# Run full pipeline on all pending files
python3 skills/audio_transcriber/scripts/run_all.py --process-all

# Run from a specific phase
python3 skills/audio_transcriber/scripts/run_all.py --from 2

# Force re-run on all files
python3 skills/audio_transcriber/scripts/run_all.py --process-all --force

# Regenerate glossary only
python3 skills/audio_transcriber/scripts/run_all.py --glossary

# Process a single subject
python3 skills/audio_transcriber/scripts/run_all.py --subject <SubjectName>
```

## Global Standards

- **Zero Temperature**: `config.yaml` enforces `temperature: 0` to guarantee deterministic, hallucination-free outputs.
- **Headless CLI**: Supports `--process-all`, `--from`, `--force`, `--resume`, `--log-json` for full CI/CD compatibility.
- **Preflight Check**: Validates all dependencies and config on every run before processing begins.
- **Checkpoint Resume**: All phase completions are saved to `state/`; use `--resume` to continue after an interruption.
- macOS native notifications (`osascript`) and graceful `KeyboardInterrupt` handling with checkpoint save.
