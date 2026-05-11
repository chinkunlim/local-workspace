# Contributing Guide

This is a private workspace. The following guidelines apply to all contributors (human and AI agents).

## Before You Start

Read the mandatory context in order:
1. `openclaw-sandbox/memory/PROJECT_RULES.md`
2. `openclaw-sandbox/memory/ARCHITECTURE.md`
3. `openclaw-sandbox/docs/CODING_GUIDELINES.md`
4. `openclaw-sandbox/AGENTS.md`

## Development Workflow

1. Create a branch: `git checkout -b feature/your-feature`
2. Make changes, keeping each commit focused on one thing
3. Run quality checks: `./openclaw-sandbox/ops/check.sh`
4. Update documentation in the same commit as code changes
5. Open a PR using the template in `.github/PULL_REQUEST_TEMPLATE.md`

## Commit Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(voice-memo): add retry logic for transcription phase
fix(core): handle empty config.yaml gracefully
docs(memory): update HANDOFF.md after session
refactor(pdf-knowledge): extract security check into core
```

## Code Standards

All code must pass `./openclaw-sandbox/ops/check.sh`:
- **Ruff** lint and format (zero warnings)
- **Mypy** type check on `core/`

See `docs/CODING_GUIDELINES.md` for full standards.
