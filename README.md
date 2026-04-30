# local-workspace (Open Claw Ecosystem)

> An Event-driven, Human-in-the-Loop (HITL), Multi-Agent Orchestration Framework for local-first AI automation.

## 🏗️ Architecture Data Flow
```mermaid
graph TD
    User([User / Inbox]) -->|File Drop / Message| Core
    Core[core/ Orchestration] -->|Parse Intent| RouterAgent
    RouterAgent -->|Generate DAG| Skills[skills/ (Pipelines)]
    Skills -->|Generate/Embed| LLM[LLM Client / Chroma]
    Skills -->|Pause for Review| HITL[HITL Manager]
    HITL -.->|Telegram Alert| User
```

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

## 🚀 Quick Start (Foolproof Setup)

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url> local-workspace
   cd local-workspace
   ```

2. **Configure Environment:**
   Copy the example environment file and fill in your API keys:
   ```bash
   cp .env.example .env
   # Edit .env with your favorite editor
   ```

3. **Install Dependencies:**
   ```bash
   cd open-claw-sandbox
   pip install pip-tools
   pip-sync requirements.txt
   cd ..
   ```

4. **Start the Infrastructure:**
   Start all services including Ollama, Open WebUI, Pipelines, and the Open Claw Daemon.
   ```bash
   ./infra/scripts/start.sh
   ```

## Service Endpoints

| Service | URL |
|---|---|
| Open WebUI | http://127.0.0.1:3000 |
| LiteLLM Proxy | http://127.0.0.1:4000 |
| Ollama | http://127.0.0.1:11434 |
| Pipelines | http://127.0.0.1:9099 |
| Open Claw API | http://127.0.0.1:18789 |

## Documentation

- `docs/USER_MANUAL.md` — The complete guide on how to use this ecosystem (Start Here)
- `docs/CODING_GUIDELINES.md` — Single source of truth for all development rules (v3.0.0)
- `memory/ARCHITECTURE.md` — Full system architecture and design decisions
- `open-claw-sandbox/AGENTS.md` — AI agent behaviour contract
- `open-claw-sandbox/docs/STRUCTURE.md` — Annotated file map of the sandbox

## Change Discipline

Any code change must be accompanied by documentation updates in the same commit. See `CONTRIBUTING.md`.
