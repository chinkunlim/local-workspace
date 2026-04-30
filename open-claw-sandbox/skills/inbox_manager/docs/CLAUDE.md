# CLAUDE.md — Inbox Manager Skill

> AI agent collaboration context for the `inbox_manager` skill.
> Read this file before making any changes to this skill or `core/config/inbox_config.json`.

## Skill Summary

`inbox_manager` is a **pure CLI configuration management utility**. It provides a safe interface
for inspecting and modifying the PDF routing rules in `core/config/inbox_config.json`.
It calls no LLM, performs no file processing, and owns no data directories.

## Key Invariants

1. **No LLM calls**: Never add AI inference to this skill. It is a config editor, not an AI skill.
2. **Atomic writes only**: All modifications to `inbox_config.json` must use `AtomicWriter`. Never use `open(path, 'w')` directly.
3. **Pattern uniqueness**: Each routing pattern (suffix) must be unique. The `--add` command must validate for duplicates before writing.
4. **Hot-reload compatible**: `inbox_daemon.py` reloads the config on every file event. Changes take effect within seconds without a daemon restart.

## File Locations

| Item | Path |
|:---|:---|
| Config target | `core/config/inbox_config.json` |
| CLI entry point | `skills/inbox_manager/scripts/query.py` |

## CLI Usage

```bash
# Show all current routing rules
python3 skills/inbox_manager/scripts/query.py --list

# Add new pattern
python3 skills/inbox_manager/scripts/query.py \
    --add "_exam" --routing both --description "Exam materials"

# Remove pattern
python3 skills/inbox_manager/scripts/query.py --remove "_exam"
```

## What NOT to Change Without Reading DECISIONS.md

- Direct edits to `core/config/inbox_config.json` — always use this skill's CLI
- The routing mode enum (`audio_ref`, `doc_parser`, `both`) — `inbox_daemon.py` depends on these exact strings
