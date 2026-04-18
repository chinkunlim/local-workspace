# DECISIONS.md — Architectural Decision Records

> **Last Updated:** 2026-04-18
> **Format:** ADR (Architectural Decision Record)

---

## [2026-04-18] Establish `memory/` as AI Reading Layer

### Background
Guidelines (§12.2) specify that AI collaboration files (CLAUDE.md, HANDOFF.md, TASKS.md, DECISIONS.md, ARCHITECTURE.md) should live in a `memory/` directory. Previously these did not exist at workspace level.

### Decision
Create `memory/` at workspace root with the five standard files. Agent startup sequence updated in `AGENTS.md` and `memory/CLAUDE.md` to reference these paths.

### Consequence
AI agents now have a standardised onboarding path. Root-level context files (AGENTS.md, IDENTITY.md, SOUL.md, USER.md) remain at root — they are workspace identity documents, not session memory.

---

## [2026-04-18] Move config files to workspace root

### Background
`pyproject.toml` and `.pre-commit-config.yaml` were in `ops/config/`. Tools like Ruff and pre-commit expect these at the project root.

### Options
1. Keep in `ops/config/` — requires `--config` flags on every tool invocation
2. Move to workspace root ✅ — standard convention, zero friction

### Decision
Move to workspace root. `ops/config/` directory deleted.

### Consequence
`ruff check .`, `mypy core/`, `pre-commit run` all work without extra flags.

---

## [2026-04-18] CODING_GUIDELINES_FINAL.md as single source of truth

### Background
Three overlapping documents existed: `BASIC_RULES.md` (v1.0), `CODING_GUIDELINES.md` (v2.0), and `CODING_GUIDELINES_FINAL.md`.

### Decision
Merge all three into `CODING_GUIDELINES_FINAL.md` v3.0.0. Delete the other two. Store in both `docs/` and workspace `docs/`.

---

## [2026-04-17] MLX-Whisper over Docker for transcription

### Background
Earlier voice-memo used a Docker-based Whisper container. Docker adds startup latency and requires a daemon running.

### Decision
Switch to MLX-Whisper (native Apple Silicon). Zero Docker dependency, lower latency, better integration with macOS power management.

### Consequence
Removed all Docker references from voice-memo pipeline and docs.

---

## [2026-04-15] Shared `core/` framework over per-skill duplication

### Background
Early voice-memo had inline logging, path resolution, and state management. Adding pdf-knowledge would duplicate all of this.

### Decision
Extract shared logic into `core/` with `PipelineBase` abstract class. Each skill phase inherits from it.

### Consequence
Adding new skills requires only implementing the phase logic; infrastructure (logging, resume, paths) is inherited automatically.

---

## [2026-04-15] Strict `data/` separation from `skills/`

### Background
Pipeline outputs were previously mixed with source code.

### Decision
All runtime data (inputs, outputs, state, logs) lives exclusively in `data/<skill>/`. Source code in `skills/<skill>/scripts/`. No cross-contamination.

### Consequence
`git clean -fd` on `skills/` is safe. Data directory excluded from git.
