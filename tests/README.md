# Tests

This directory contains workspace-level integration and end-to-end tests.

## Structure

```
tests/
├── e2e/           ← End-to-end tests (full pipeline runs)
└── integration/   ← Cross-module integration tests
```

## Skill-Level Unit Tests

Unit tests for each skill live inside the skill directory:
- `openclaw-sandbox/skills/voice-memo/tests/`
- `openclaw-sandbox/skills/pdf-knowledge/tests/`

## Running Tests

```bash
# E2E — run a full voice-memo pipeline
cd openclaw-sandbox
python skills/voice-memo/scripts/run_all.py --subject test_subject

# Integration — verify core modules load correctly
python -c "from core import pipeline_base, path_builder, log_manager; print('Core OK')"
```
