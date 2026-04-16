# AGENTS.md

## 1. Mission

Deliver production-grade local AI automation with explicit safety, auditability, and maintainability.
All agents operate within the open-claw-workspace sandbox boundary.

## 2. Mandatory Startup Context for Agents

Before making any change, read and apply the following files in order:

1. `docs/CODING_GUIDELINES.md` — engineering contract, naming rules, tooling
2. `SOUL.md` — quality and discipline principles
3. `USER.md` — operator profile and preferences
4. `docs/STRUCTURE.md` — annotated map of every file and folder in this workspace
5. `skills/<skill>/SKILL.md` — skill quick-start, phases, and CLI reference
6. `skills/<skill>/docs/ARCHITECTURE.md` — current verified architecture and data flow

## 3. Non-Negotiable Behaviors

1. Do not execute destructive actions without explicit operator approval.
2. Do not leak private data outside the local sandbox boundary.
3. Prefer deterministic scripts and explicit logs over hidden or implicit behavior.
4. Keep all changes minimal and scoped to the stated objective.
5. Update documentation in the same change set for any significant modification.
6. Never reference or modify files outside `open-claw-workspace/` from within skill code.

## 4. Documentation Update Requirement

If code changes affect observable behavior, update corresponding documentation immediately:

| Changed behaviour | Files to update |
|:---|:---|
| CLI interface change | `skills/<skill>/SKILL.md` |
| Data path, phase logic, or core module change | `skills/<skill>/docs/ARCHITECTURE.md` + `docs/STRUCTURE.md` |
| Architectural decision made | `skills/<skill>/docs/DECISIONS.md` |
| New pattern or rule established | `docs/CODING_GUIDELINES.md` |
| New skill or core module added | `docs/STRUCTURE.md`, `skills/SKILL.md` |

## 5. External Action Policy

Request explicit operator approval before any action that leaves the machine:
email, public posting, external service mutation, or any operation outside the local network control plane.

## 6. Quality Bar

All outputs — code, documentation, and plans — must be:
- Professional and concise
- Verifiable by future operators
- Interoperable across Claude Code, GitHub Copilot, and Google Antigravity
- Compliant with `docs/CODING_GUIDELINES.md` in full

## 7. Sandbox Invariant

`open-claw-workspace/` is a fully self-contained sandbox. See `docs/CODING_GUIDELINES.md` Section 5 for the full isolation specification.
