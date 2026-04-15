# PDF Knowledge Architecture

Last Updated: 2026-04-15
Owner: pdf-knowledge maintainers

## 1. Scope
PDF Knowledge ingests academic PDF files and produces structured, verifiable knowledge outputs through staged extraction and operator-aware processing.

## 2. Functional Pipeline
1. Phase 1a lightweight PDF diagnostic
2. Phase 1b deep extraction
3. Phase 1c vector chart supplementation
4. Phase 1d OCR quality gate
5. Queue-driven processing and resume lifecycle
6. Dashboard-assisted operations

## 3. Data Flow
Canonical model:
- input/01_Inbox
- output/02_Processed
- output/03_Agent_Core
- output/05_Final_Knowledge
- state
- logs

## 4. Core Runtime Features
- Shared PipelineBase orchestration
- ResumeManager for interruption recovery
- Security policy boundaries for browser automation
- ModelMutex for resource contention prevention
- Atomic report and artifact writes

## 5. Reliability Controls
- Early diagnostic fail-fast strategy
- Immutable raw extraction artifacts
- OCR confidence scoring and warning propagation
- Error isolation into dedicated failure paths

## 6. Current Gaps Compared to Voice Skill
- No comparable interactive CLI phase walk for human review checkpoints
- No explicit synthesis anti-content-loss guard equivalent
- No unified checklist rendering equivalent to voice-memo state table

## 7. Complement Plan
High priority:
1. Add synthesis-stage anti-content-loss guard.
2. Add optional interactive phase checkpoint mode.
3. Add explicit phase checklist rendering for operator parity.
