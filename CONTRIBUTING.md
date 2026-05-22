# Contributing Guide

This is a private workspace. The following guidelines apply to all contributors (human and AI agents).

## Before You Start

Read the mandatory context in order:
1. `memory/PROJECT_RULES.md`
2. `memory/HANDOFF.md`
3. `docs/ARCHITECTURE.md`
4. `docs/CODING_GUIDELINES.md`
5. `openclaw-sandbox/AGENTS.md`
6. `openclaw-sandbox/HEARTBEAT.md` (run health checks)

## Development Workflow

1. Create a branch: `git checkout -b feature/your-feature`
2. Make changes, keeping each commit focused on one thing
3. Run quality checks: `./openclaw-sandbox/ops/check.sh`
4. Update documentation in the same commit as code changes
5. Open a PR using the template in `.github/PULL_REQUEST_TEMPLATE.md`

## Commit Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(audio_transcriber): add retry logic for transcription phase
fix(core): handle empty config.yaml gracefully
docs(memory): update HANDOFF.md after session
refactor(doc_parser): extract security check into core
```

## Code Standards

All code must pass `./ops/check.sh` (run via `uv run` inside `openclaw-sandbox/`):
- **Ruff** lint and format (zero warnings)
- **Mypy** type check on `core/ + skills/` (all 147 source files)

See `docs/CODING_GUIDELINES.md` (v4.2.0) for full standards.
