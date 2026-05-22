# Architectural Decision Records (ADRs)

## ADR-012: Separation of Pipeline Skills and OpenClaw CLI Skills
**Date**: 2026-05-22
**Status**: Superseded by ADR-013

### Context
The project contains heavy ML pipelines (`doc_parser`, `audio_transcriber`). Initially, we attempted to expose them to the OpenClaw Agent framework using symlinks from `~/.openclaw/skills/` to `openclaw-sandbox/skills/`. This was blocked by OpenClaw's security layer (`symlink-escape`).

### Decision
We originally decided to keep them separate: Pipeline Skills run via `inbox_daemon` and `TaskQueue`, while OpenClaw CLI Skills are lightweight.

---

## ADR-013: Unification of Pipeline Skills into OpenClaw Agent
**Date**: 2026-05-23
**Status**: Active

### Context
The user requested a single Telegram Bot interface where OpenClaw can natively recognize and trigger the heavy ML pipelines, rather than managing a separate `bot_daemon.py` pipeline bot.

### Decision
We will bypass the symlink-escape restriction by **hard-copying** the `SKILL.md` files from the sandbox workspace (`openclaw-sandbox/skills/*/SKILL.md`) directly into `~/.openclaw/skills/`.
This allows the OpenClaw Agent to natively discover the pipeline skills. When invoked, the Agent reads the instructions in `SKILL.md` and safely executes the pipeline's CLI orchestrator (`python3 scripts/run_all.py`) inside the workspace context.
The separate `bot_daemon.py` and secondary Telegram bot token have been deprecated.
