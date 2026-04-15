# Voice Memo Walkthrough

## 1. Preconditions
1. Dependencies installed.
2. Ollama runtime available.
3. Input audio in data/voice-memo/input/raw_data.
4. Config values present in skills/voice-memo/config/config.yaml.

## 2. Run Pipeline
Command:
python3 skills/voice-memo/scripts/run_all.py

Common options:
- --subject <name>
- --from <phase>
- --resume
- --interactive
- --force

## 3. Observe Outputs
- Transcripts: data/voice-memo/output/01_transcript
- Proofread: data/voice-memo/output/02_proofread
- Merged: data/voice-memo/output/03_merged
- Highlighted: data/voice-memo/output/04_highlighted
- Synthesis: data/voice-memo/output/05_notion_synthesis

## 4. Observe State and Logs
- State: data/voice-memo/state/.pipeline_state.json
- Checklist: data/voice-memo/state/checklist.md
- Logs: data/voice-memo/logs/system.log

## 5. Resume After Interrupt
1. Re-run with --resume.
2. Confirm checkpoint prompt and continue.
3. Validate no duplicate work for completed phase outputs.
