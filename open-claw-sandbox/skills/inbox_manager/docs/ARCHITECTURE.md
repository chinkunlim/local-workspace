# inbox_manager — Architecture

## Role

`inbox_manager` is a **CLI utility skill** for managing the PDF routing rules in
`core/config/inbox_config.json`. It provides a clean command-line interface so that
operators never need to manually edit JSON. It performs **no file processing** and
calls **no LLM** — it is a pure configuration management tool.

## Design Principles

1. **No LLM, No AI**: This skill is a pure data-management CLI. Never add LLM calls.
2. **Single Config File**: All routing rules live in `core/config/inbox_config.json`.
   This skill is the only sanctioned way to modify that file at runtime.
3. **Atomic Writes**: All config updates use `core.utils.atomic_writer.AtomicWriter`
   to prevent JSON corruption if the process is interrupted.
4. **Human-Readable Output**: All `list` operations format output as a readable table,
   not raw JSON.

## Routing Modes

| Mode | Behaviour |
|:---|:---|
| `audio_ref` | PDF is linked into `audio_transcriber/input/` as a proofreading reference. No standalone parsing. |
| `doc_parser` | PDF is sent to `doc_parser/input/` for full Markdown extraction. |
| `both` | PDF is atomically copied to BOTH destinations simultaneously. |

## Processing Flow

```
CLI Command (query.py)
  │
  ├── --list   → Read inbox_config.json → Format as table → stdout
  ├── --add    → Validate input → Append rule to inbox_config.json (AtomicWriter)
  └── --remove → Find rule by pattern → Remove → Rewrite inbox_config.json (AtomicWriter)
```

## Directory Structure

```
skills/inbox_manager/
├── SKILL.md              ← Quick-start: all CLI commands
├── docs/
│   ├── ARCHITECTURE.md   ← This file
│   ├── CLAUDE.md         ← AI agent collaboration context
│   └── DECISIONS.md      ← Technical decision log
└── scripts/
    └── query.py          ← Main CLI entry point (list / add / remove)
```

## CLI Commands

```bash
# List all active routing rules
python3 skills/inbox_manager/scripts/query.py --list

# Add a new audio_ref pattern
python3 skills/inbox_manager/scripts/query.py \
    --add "_ppt" --routing audio_ref --description "PowerPoint slides"

# Add a 'both' pattern (parse + audio reference)
python3 skills/inbox_manager/scripts/query.py \
    --add "_textbook" --routing both --description "Course textbooks"

# Remove a pattern
python3 skills/inbox_manager/scripts/query.py --remove "_ppt"
```

## Config File Location

`core/config/inbox_config.json` — managed exclusively by this skill at runtime.
The `inbox_daemon.py` hot-reloads this file on every file event; no daemon restart is required.

## Dependencies

| Module | Purpose |
|:---|:---|
| `core.utils.atomic_writer.AtomicWriter` | Corruption-safe JSON writes |
| `core.config.config_manager` | Config loading utilities |
