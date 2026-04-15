# Open Claw Engineering and Documentation Standard

Version: 2026-04-15
Scope: Entire open-claw-workspace (core, skills, scripts, docs, and operations)

## 1. Purpose
This document is the mandatory contract for all AI coding agents and human contributors.
The goal is production-grade reliability on local hardware, with explicit auditability, deterministic behavior, and clean handoff across Claude Code, Copilot, and Google Antigravity workflows.

## 2. Architecture Rules
1. Local-first only. Do not introduce cloud-only dependencies as required runtime paths.
2. All skill execution code must inherit from core.pipeline_base.PipelineBase or a direct shared core abstraction.
3. Shared logic belongs in core, not duplicated under skills.
4. Canonical data layout is mandatory for each skill:
   - input
   - output
   - state
   - logs
5. Legacy folder names may exist only as compatibility aliases during migration.

## 3. Configuration Rules
1. No hardcoded runtime values in Python for model names, thresholds, URLs, or critical paths.
2. Required config keys must fail fast through core/config_validation.py.
3. Do not silently fallback for missing critical values.
4. Keep config machine-readable and deterministic.

## 4. Reliability and Safety Rules
1. State and checkpoint writes must be atomic.
2. Long-running steps must support interruption and deterministic resume semantics.
3. Resource guards are required before and during heavy tasks:
   - RAM
   - Disk
   - Temperature
   - Battery (when applicable)
4. Security boundaries must be explicit for browser or network automation.

## 5. Logging Rules
1. All runtime operations must produce logs.
2. Use shared logger tooling from core/log_manager.py.
3. Workspace-level logs:
   - start.sh -> logs/startup.log
   - stop.sh -> logs/stop.log
   - watchdog.sh -> logs/ram_watchdog.log
4. Skill-level logs:
   - data/<skill>/logs/system.log
   - Additional scoped logs allowed when justified (for example dashboard.log, security_audit.log)
5. Log lines must allow incident reconstruction without guessing.

## 6. Code Quality Rules
1. Type hints are required for non-trivial functions.
2. Comments must explain intent or risk, not obvious syntax.
3. Keep side effects explicit.
4. Preserve deterministic ordering for batch processing.
5. Preserve public API compatibility unless migration notes are written.

## 7. Documentation Contract (Mandatory)
For every significant change, update documentation in the same commit.

### 7.1 Required Files
At minimum, update these files when relevant:
- skills/<skill_name>/SKILL.md
- skills/<skill_name>/docs/ARCHITECTURE.md
- skills/<skill_name>/docs/DECISIONS*.md
- skills/<skill_name>/docs/HANDOFF*.md
- skills/<skill_name>/docs/PROGRESS*.md
- skills/<skill_name>/docs/TASKS*.md
- skills/<skill_name>/docs/WALKTHROUGH*.md

### 7.2 Writing Standard for skills/<skill_name>/docs/*.md
All docs in skills/<skill_name>/docs/*.md must follow these rules:
1. Use English as the primary language for precision and multi-agent interoperability.
2. Use clear section headers with stable names.
3. Distinguish facts, decisions, and plans.
4. Every decision entry must include:
   - decision id
   - date
   - rationale
   - impact
   - affected files
5. Every handoff file must include:
   - current state
   - next actions
   - known risks
   - verification status
6. Every progress file must be chronological and immutable for past milestones.
7. Every tasks file must separate:
   - active
   - queued
   - blocked
   - done
8. Every walkthrough file must be executable by a new operator without hidden assumptions.
9. Use exact script names and paths. Avoid vague wording.
10. Record constraints and failure modes explicitly.

### 7.3 AI Professional Output Grade
Documentation and code must meet professional standards expected from:
- Claude Code
- GitHub Copilot
- Google Antigravity

This means:
1. No fluff.
2. No contradictory statements.
3. No stale instructions.
4. No ambiguous ownership.
5. No missing operational context.

## 8. Language Policy for Markdown
Recommended policy for this repository:
1. English-first for technical docs and cross-agent consistency.
2. Optional bilingual notes allowed only when operator context requires it.
3. If bilingual, English must remain canonical and complete.

## 9. Review Gate Before Merge
Before considering a change complete:
1. Runtime errors check passes for touched files.
2. Operational scripts parse correctly (for shell changes).
3. Docs are updated and internally consistent.
4. Logging and resume behavior remain intact.
5. A rollback path is clear.
