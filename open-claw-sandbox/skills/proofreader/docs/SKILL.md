# Proofreader Skill

## Overview
The `proofreader` skill is a centralized module responsible for ensuring the accuracy and completeness of generated transcripts against reference materials (e.g., PDF lecture slides or PNG materials). It coordinates across the outputs of `audio_transcriber` and `doc_parser`.

## Phases

### `p01_transcript_proofread.py`
Reads the merged transcript from the `audio_transcriber` and checks the `.session_manifest.json` for reference materials.
- **with_reference mode**: Uses parsed documents to correct specialized terminology and spelling.
- **semantic_only mode**: Corrects spelling based purely on context.
- **wait**: If materials are still processing, it halts execution until triggered.

### `p02_doc_completeness.py`
Validates that all key topics and visual charts from the reference material are mentioned in the transcript.
- Embeds images into the transcript where appropriate.
- Adds `> [!NOTE]` blocks for any critical information from the reference that was omitted by the speaker.

## Usage
Triggered automatically via the `RouterAgent` or manually:
```bash
python scripts/run_all.py --subject [SubjectName]
```
