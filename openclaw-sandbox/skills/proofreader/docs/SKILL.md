# Proofreader Skill

## Overview
The `proofreader` skill is a centralized module responsible for ensuring the accuracy and completeness of generated transcripts against reference materials (e.g., PDF lecture slides or PNG materials). It coordinates across the outputs of `audio_transcriber` and `doc_parser`.

## Phases

### `p00_doc_proofread.py` (Phase 0)
Designed specifically for `doc_parser` output. Corrects OCR errors and mathematically embeds extracted images/diagrams exactly where they logically belong in the Markdown text.

### `p01_transcript_proofread.py` (Phase 1)
Reads the merged transcript from the `audio_transcriber` and checks the `.session_manifest.json` for reference materials.
- **with_reference mode**: Uses parsed documents to correct specialized terminology and spelling.
- **semantic_only mode**: Corrects spelling based purely on context.

### `p02_doc_completeness.py` (Phase 2)
Validates that all key topics and visual charts from the reference material are mentioned in the transcript.
- Embeds images into the transcript where appropriate.
- Adds `> [!NOTE]` blocks for any critical information from the reference that was omitted by the speaker.

## Asynchronous Verification Dashboard
Proofreader uses a non-blocking Human-in-the-Loop approach. Instead of pausing the pipeline, completed drafts are placed in `data/proofreader/output/`. 
Users can run the dashboard at their convenience:
```bash
python scripts/dashboard.py
```
This launches a centralized Web UI (http://localhost:8080) to review AI corrections side-by-side with original Ground Truth media (PDF, PNG, M4A).

## Usage
Triggered automatically via the `RouterAgent` or manually:
```bash
python scripts/run_all.py --subject [SubjectName]
```
