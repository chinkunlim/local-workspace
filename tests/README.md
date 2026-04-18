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
- `open-claw-workspace/skills/voice-memo/tests/`
- `open-claw-workspace/skills/pdf-knowledge/tests/`

## Running Tests

```bash
# E2E — run a full voice-memo pipeline
cd open-claw-workspace
python skills/voice-memo/scripts/run_all.py --subject test_subject

# Integration — verify core modules load correctly
python -c "from core import pipeline_base, path_builder, log_manager; print('Core OK')"
```
