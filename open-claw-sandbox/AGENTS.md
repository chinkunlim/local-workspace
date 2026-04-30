# AGENTS.md

## 1. Mission

Deliver production-grade local AI automation with explicit safety, auditability, and maintainability.
All agents operate within the open-claw-sandbox sandbox boundary.

## 2. Mandatory Startup Context for Agents

Before making any change, read and apply the following files in order:

1. `memory/CLAUDE.md` — project rules, AI behaviour contract, hardware constraints
2. `memory/ARCHITECTURE.md` — system architecture, module map, data flow
3. `memory/HANDOFF.md` — last session progress and next steps
4. `memory/TASKS.md` — current task list
5. `docs/STRUCTURE.md` — annotated map of every file and folder in this workspace
6. `open-claw-sandbox/AGENTS.md` — this file (non-negotiable behaviours and quality bar)
7. `skills/<skill>/SKILL.md` — skill quick-start, phases, and CLI reference (if executing a skill)

## 3. Non-Negotiable Behaviors

1. Do not execute destructive actions without explicit operator approval.
2. Do not leak private data outside the local sandbox boundary.
3. Prefer deterministic scripts and explicit logs over hidden or implicit behavior.
4. Keep all changes minimal and scoped to the stated objective.
5. Update documentation in the same change set for any significant modification.
6. Never reference or modify files outside `open-claw-sandbox/` from within skill code.

## 4. Documentation Update Requirement

If code changes affect observable behavior, update corresponding documentation immediately:

| Changed behaviour | Files to update |
|:---|:---|
| CLI interface change | `skills/<skill>/SKILL.md` |
| Data path, phase logic, or core module change | `skills/<skill>/docs/ARCHITECTURE.md` + `docs/STRUCTURE.md` |
| Architectural decision made | `skills/<skill>/docs/DECISIONS.md` |
| New pattern or rule established | `docs/CODING_GUIDELINES_FINAL.md` |
| New skill or core module added | `docs/STRUCTURE.md`, `docs/ARCHITECTURE.md`, `skills/<skill>/SKILL.md` |

## 5. External Action Policy

Request explicit operator approval before any action that leaves the machine:
email, public posting, external service mutation, or any operation outside the local network control plane.

## 6. Quality Bar

All outputs — code, documentation, and plans — must be:
- Professional and concise
- Verifiable by future operators
- Interoperable across Claude Code, GitHub Copilot, and Google Antigravity
- Compliant with `docs/CODING_GUIDELINES_FINAL.md` in full

## 7. Sandbox Invariant

`open-claw-sandbox/` is a fully self-contained sandbox. See `docs/CODING_GUIDELINES_FINAL.md` §3.4 for the full isolation specification.
