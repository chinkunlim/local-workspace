# local-workspace

Local AI operations workspace for OpenClaw, Open WebUI, LiteLLM routing, and skill-oriented automation.

## 1. What This Workspace Contains
- open-claw-sandbox: Skill framework and domain pipelines (voice-memo, pdf-knowledge)
- open-webui: Local UI and vector data runtime
- litellm: Gateway and model routing
- pipelines: Additional pipeline server runtime
- project_dev: Project work logs and handoff packs

## 2. Start and Stop
- Start all primary services:
  - ./start.sh
- Stop all primary services:
  - ./stop.sh
- Optional watchdog:
  - ./watchdog.sh

## 3. Logging
Workspace-level logs are stored in logs:
- startup.log
- stop.log
- ram_watchdog.log
- service-specific logs (litellm.log, open-webui.log, pipelines.log, openclaw.log)

Skill-level logs are under data/<skill>/logs in open-claw-sandbox.

## 4. OpenClaw Structure
See open-claw-sandbox/AGENTS.md and open-claw-sandbox/docs/CODING_GUIDELINES.md for contributor and agent contracts.

## 5. Documentation Language Policy
English is the primary language for technical documentation to maximize clarity across AI tooling and future contributors.

## 6. Change Discipline
When code changes are made in open-claw-sandbox, update:
- related skill docs in skills/<skill>/docs/*.md
- open-claw-sandbox/docs/CODING_GUIDELINES.md when standards change
- handoff and progress artifacts for operational continuity
