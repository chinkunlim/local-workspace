# CLAUDE.md — Project Rules & AI Behaviour Contract

> **Last Updated:** 2026-04-18
> **Workspace:** `open-claw-sandbox/`
> **Stack:** Python 3.9+, Ollama, Flask, MLX-Whisper, Docling, Playwright, YAML config

---

## Project Overview

`open-claw-sandbox` is a production-grade local AI automation sandbox running on macOS with 16 GB RAM.
It orchestrates two skills — **audio_transcriber** and **doc_parser** — through a shared `core/` framework,
with a Central Dashboard (port 5001) and a background Inbox Daemon for automatic file processing.

**Tech stack:**
- Language: Python
- LLM Backend: Ollama (Qwen3:14B, gemma3:12b)
- Transcription: MLX-Whisper (native, no Docker)
- PDF Extraction: Docling
- Web UI: Flask (port 5001)
- Linting: Ruff + Mypy
- Config: YAML per skill

---

## AI Agent Behaviour Rules

1. **Read-Before-Write.** Before modifying any module, read the module and its docs.
2. **No Assumptions.** Always list directories to confirm files exist before referencing them.
3. **No Silent Changes.** Every logic change must be reflected in documentation in the same commit.
4. **Service Reload Confirmation.** After any code change, confirm the affected service has reloaded.
5. **Commit Discipline.** Commit after each verified change using Conventional Commits format.
6. **Hygiene.** No `.bak`, `.tmp`, `print()` debug statements, or large commented-out blocks.
7. **Sandbox Boundary.** Skill code must never reference paths outside `open-claw-sandbox/`.

---

## Mandatory Startup Sequence

```
1. memory/CLAUDE.md          (this file)
2. memory/ARCHITECTURE.md    (system architecture)
3. memory/HANDOFF.md         (last session progress)
4. memory/TASKS.md           (current task list)
5. docs/STRUCTURE.md         (full file map)
6. AGENTS.md                 (agent behaviour contract)
7. skills/<skill>/SKILL.md   (if executing a specific skill)
```

---

## Prohibited Actions

- Do not execute destructive actions without explicit operator approval
- Do not leak private data outside the local sandbox boundary
- Do not modify `.env` or files containing real credentials
- Do not push directly to `main` without verification
- Do not leave `migrate_*.py` or one-off scripts in `ops/` after use

---

## Documentation Update Triggers

| Changed Behaviour | Files to Update |
|:---|:---|
| CLI interface change | `skills/<skill>/SKILL.md` |
| Data path, phase logic, or core module change | `skills/<skill>/docs/ARCHITECTURE.md` + `docs/STRUCTURE.md` |
| Architectural decision | `skills/<skill>/docs/DECISIONS.md` + `memory/DECISIONS.md` |
| New pattern or rule | `docs/CODING_GUIDELINES.md` |
| New skill or core module added | `docs/STRUCTURE.md`, `memory/ARCHITECTURE.md` |

---

## Hardware Constraints

- **RAM:** 16 GB — strictly one heavy model at a time (Qwen3:14B or gemma3:12b, not both)
- **Watchdog:** Monitors memory via speculative pages; evicts models if threshold exceeded
- **Platform:** macOS Apple Silicon — use MLX-native tools where possible
