# Voice Memo Architecture

Last Updated: 2026-04-15
Owner: voice-memo maintainers

## 1. Scope
Voice Memo converts lecture audio into structured study knowledge through a deterministic multi-phase pipeline.

## 2. Functional Pipeline
1. Phase 0 Glossary Candidate Generation
2. Phase 1 Transcription
3. Phase 2 Contextual Proofread
4. Phase 3 Merge and Speaker Structuring
5. Phase 4 Emphasis and Highlight
6. Phase 5 Structured Knowledge Synthesis

## 3. Data Flow
Canonical model:
- input/raw_data
- output/01_transcript
- output/02_proofread
- output/03_merged
- output/04_highlighted
- output/05_notion_synthesis
- state/.pipeline_state.json
- state/checklist.md
- logs/system.log

## 4. Core Runtime Features
- Shared PipelineBase orchestration
- Config-driven model and thresholds
- Atomic state persistence
- Resume-aware task selection
- Health checks (RAM, disk, battery, temperature)

## 5. Reliability Controls
- Verbatim guard in correction and merge stages
- Anti-tampering protection in highlight stage
- Mermaid retry loop in synthesis
- Explicit skip and force semantics

## 6. Current Gaps Compared to PDF Skill
- No dedicated lightweight preflight diagnostic for audio quality and metadata anomalies
- No security policy layer equivalent to browser safety model
- No dashboard-level observability equivalent to PDF dashboard

## 7. Complement Plan
High priority:
1. Add phase0 diagnostic preflight for media and metadata validation.
2. Add optional policy guard for constrained external lookups.
3. Add richer audit stream per phase with normalized event schema.
