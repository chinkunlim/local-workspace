# Skill Parity Analysis: voice-memo vs pdf-knowledge

Date: 2026-04-15
Scope: open-claw-workspace skills and shared core integration

## 1. Executive Summary
Both skills are now aligned on shared core contracts (config loading, validation patterns, logging model, and path governance), but they still differ in operational strengths.

voice-memo is stronger in interactive pipeline control and content integrity guards.
pdf-knowledge is stronger in preflight diagnostics, security boundaries, and dashboard observability.

The correct strategy is not to merge workflows. Keep skills separate, continue extracting shared primitives to core.

## 2. Feature Comparison

### 2.1 Flow Model
- voice-memo: linear, phase-ordered transcript-to-knowledge pipeline
- pdf-knowledge: staged extraction with queue orchestration and resumable processing

### 2.2 State and Resume
- voice-memo: phase-level state tracking and checklist semantics
- pdf-knowledge: per-item resume state and queue-aware recovery

### 2.3 Safety and Resource Controls
- voice-memo: strong runtime resource checks and anti-content-loss guard in highlight stage
- pdf-knowledge: strong model mutex and browser-policy safety boundaries

### 2.4 Security
- voice-memo: no dedicated security policy layer equivalent to browser workload
- pdf-knowledge: explicit security policy and auditable action boundaries

### 2.5 Logging and UX
- voice-memo: robust CLI-centric operations
- pdf-knowledge: dashboard-centric operations with API-facing status surfaces

## 3. Complement Opportunities

### High Priority
1. Add voice-memo preflight diagnostic phase for media-level quality checks.
2. Add pdf-knowledge synthesis anti-content-loss guard equivalent to voice-memo highlight protection.
3. Add voice-memo policy guard layer for constrained external integrations.

### Medium Priority
1. Add interactive review checkpoints in pdf queue manager.
2. Add explicit checklist rendering in pdf pipeline similar to voice state visibility.
3. Add cross-skill glossary sync mechanism for shared terminology.

### Lower Priority
1. Add optional voice dashboard for parity with pdf operations.
2. Add normalized event schema for both skills to support richer observability and postmortem workflows.

## 4. Implementation Targets
- voice-memo:
  - skills/voice-memo/scripts/run_all.py
  - skills/voice-memo/scripts/phases/
  - skills/voice-memo/config/
- pdf-knowledge:
  - skills/pdf-knowledge/scripts/queue_manager.py
  - skills/pdf-knowledge/scripts/main_app.py
  - skills/pdf-knowledge/scripts/
- shared core:
  - core/config_validation.py
  - core/error_classifier.py
  - core/log_manager.py
  - core/cli.py
  - core/data_layout.py

## 5. Language Policy Decision
For this repository, English-first technical docs are preferred for multi-agent interoperability and clearer long-term maintenance.
If bilingual notes are required for operators, keep English as canonical and complete.
