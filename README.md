# local-workspace

Local AI operations monorepo — Open Claw automation sandbox, LLM infrastructure, and skill-oriented pipelines.

## Structure

```
local-workspace/
├── open-claw-sandbox/   ← Open Claw AI automation (voice-memo, pdf-knowledge)
├── infra/               ← LiteLLM proxy, Open WebUI, Pipelines, lifecycle scripts
├── docs/                ← Global documentation (CODING_GUIDELINES_FINAL, AI_Master_Guide)
├── memory/              ← Global AI memory (ARCHITECTURE, DECISIONS)
├── ops/                 ← Global quality gate (check.sh)
└── tests/               ← E2E and integration test stubs
```

## Quick Start

```bash
# Start all services (Ollama, LiteLLM, Open WebUI, Pipelines, Open Claw Dashboard)
./infra/scripts/start.sh

# Stop all services
./infra/scripts/stop.sh

# RAM watchdog (optional — auto-evicts models when memory is low)
./infra/scripts/watchdog.sh

# Run full quality check
./ops/check.sh
```

## Service Endpoints

| Service | URL |
|---|---|
| Open Claw Dashboard | http://127.0.0.1:5001 |
| Open WebUI | http://127.0.0.1:3000 |
| LiteLLM Proxy | http://127.0.0.1:4000 |
| Ollama | http://127.0.0.1:11434 |
| Pipelines | http://127.0.0.1:9099 |

## Logs

- Service logs: `logs/` (startup.log, openclaw.log, litellm.log, etc.)
- Skill logs: `open-claw-sandbox/data/<skill>/logs/`

## Documentation

- `docs/USER_MANUAL.md` — The complete guide on how to use this ecosystem (Start Here)
- `docs/CODING_GUIDELINES_FINAL.md` — Single source of truth for all development rules (v3.0.0)
- `memory/ARCHITECTURE.md` — Full system architecture and design decisions
- `open-claw-sandbox/AGENTS.md` — AI agent behaviour contract
- `open-claw-sandbox/docs/STRUCTURE.md` — Annotated file map of the sandbox

## Change Discipline

Any code change must be accompanied by documentation updates in the same commit. See `CONTRIBUTING.md`.
