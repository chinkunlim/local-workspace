# ARCHITECTURE.md — Global System Architecture

> **Scope:** Entire `local-workspace/` monorepo
> **Last Updated:** 2026-04-19
> **Audience:** All AI agents operating in this workspace

---

## System Overview

`local-workspace/` is a private monorepo that hosts a local AI automation ecosystem on macOS (16 GB RAM, Apple Silicon). It orchestrates several infrastructure services and one primary application sandbox.

```
local-workspace/                    ← Monorepo root (git repo)
│
├── open-claw-sandbox/              ← Primary App: Open Claw AI Automation
│   ├── core/                       ← Shared Python framework
│   ├── skills/                     ← voice-memo, pdf-knowledge pipelines
│   ├── memory/                     ← Sandbox-level AI memory (CLAUDE, HANDOFF, TASKS...)
│   ├── docs/                       ← Sandbox documentation (STRUCTURE, CODING_GUIDELINES)
│   └── ops/                        ← Sandbox quality checks (check.sh, bootstrap.sh)
│
├── infra/                          ← Infrastructure layer (LLM services, UI, proxy)
│   ├── litellm/                    ← LiteLLM OpenAI-compatible proxy (port 4000)
│   ├── open-webui/                 ← Open WebUI chat interface (port 3000)
│   ├── pipelines/                  ← Open WebUI Pipeline runner (port 9099)
│   └── scripts/                   ← Lifecycle scripts: start.sh, stop.sh, watchdog.sh
│
├── docs/                           ← Global documentation
│   ├── CODING_GUIDELINES_FINAL.md  ← Single source of truth for all development rules (v3.0.0)
│   └── AI_Master_Guide_Final.md    ← System-wide AI ecosystem guide (v9)
│
├── memory/                         ← Global AI memory (this directory)
│   ├── ARCHITECTURE.md             ← This file
│   └── DECISIONS.md                ← Global architectural decisions
│
└── ops/                            ← Global quality scripts
    └── check.sh                    ← Full monorepo quality gate
```

---

## Design Decisions (Summary)

### Why `open-claw-sandbox/` is NOT inside `apps/`

§11.2 of CODING_GUIDELINES_FINAL recommends an `apps/` directory for independently runnable subsystems. However, `open-claw-sandbox/` is placed directly at the monorepo root because:

1. It is the **only** application in this monorepo (no sibling apps)
2. It contains its own mature internal structure (`core/`, `skills/`, `memory/`, `ops/`)
3. Adding an `apps/` wrapper adds indirection with no benefit at this scale
4. `WORKSPACE_DIR` environment variables already point directly to the sandbox

**If a second application is added in the future**, create `apps/` and move both into it at that time.

### Why `pipelines/` is in `infra/` (not `apps/`)

Open WebUI Pipelines is infrastructure (a plugin runner for the LLM proxy), not an application with user-facing logic. It belongs with the other infrastructure services in `infra/`.

### Strict Extraction vs Processing Boundaries

Skills are strictly divided into **Extraction** and **Processing** layers.
- **Extraction Skills** (`audio-transcriber`, `doc-parser`): Responsible ONLY for generating high-fidelity Markdown from raw files. They must not perform summarization, highlighting, or formatting.
- **Processing Skills** (`smart_highlighter`, `note_generator`): Responsible for taking raw Markdown and applying stylistic highlights, generating Cornell notes, or mapping core concepts.
- **I/O Routing**: The `inbox_daemon` routes files purely by extension into a skill's `input/` directory. Direct writing to another skill's `output/` directory is strictly forbidden.

---

## Service Map

| Service | Port | Directory | Started by |
|---|---|---|---|
| Ollama (LLM) | 11434 | system install | `infra/scripts/start.sh` |
| LiteLLM Proxy | 4000 | `infra/litellm/` | `infra/scripts/start.sh` |
| Open WebUI | 3000 | `infra/open-webui/` | `infra/scripts/start.sh` |
| Pipelines | 9099 | `infra/pipelines/` | `infra/scripts/start.sh` |
| Open Claw Dashboard | 5001 | `open-claw-sandbox/core/web_ui/` | `infra/scripts/start.sh` |
| Inbox Daemon | — | `open-claw-sandbox/core/inbox_daemon.py` | `infra/scripts/start.sh` |
| Watchdog (RAM guard) | — | `infra/scripts/watchdog.sh` | `infra/scripts/start.sh` |

---

## AI Agent Entry Points

| Agent starting point | When to use |
|---|---|
| `memory/ARCHITECTURE.md` (this file) | Understanding the whole monorepo |
| `open-claw-sandbox/memory/CLAUDE.md` | Working inside the sandbox |
| `open-claw-sandbox/AGENTS.md` | Sandbox rules and behaviour contract |
| `docs/CODING_GUIDELINES_FINAL.md` | Development standards |
