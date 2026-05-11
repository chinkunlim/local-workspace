---
name: inbox_manager
description: Manages the Inbox routing rules for the Open Claw ecosystem. Use this to list, add, or remove PDF routing suffixes without editing files manually.
metadata:
  {
    "openclaw":
      {
        "emoji": "📬"
      }
  }
---

# Inbox Manager

A utility skill for managing how files dropped into `data/raw/` are automatically routed to the correct processing pipelines.

## What it Does

- **Lists** all current routing rules (suffix → destination)
- **Adds** new patterns to the PDF routing rules
- **Removes** patterns you no longer need

## Configuration File

All rules live in `core/inbox_config.json`. This skill provides a clean CLI interface so you never need to edit JSON manually.

## CLI Usage

```bash
# Show all current routing rules
python3 skills/inbox_manager/scripts/query.py --list

# Add a new audio_ref pattern
python3 skills/inbox_manager/scripts/query.py --add "_ppt" --routing audio_ref --description "PowerPoint slides"

# Add a 'both' pattern (doc_parser + audio ref)
python3 skills/inbox_manager/scripts/query.py --add "_units" --routing both --description "Course units"

# Remove a pattern
python3 skills/inbox_manager/scripts/query.py --remove "_ppt"
```

## Routing Modes

| Mode | Behaviour |
|---|---|
| `audio_ref` | PDF sent to audio_transcriber as a proofreading reference only |
| `doc_parser` | PDF sent to doc_parser for full Markdown extraction |
| `both` | PDF copied to BOTH destinations simultaneously |

## Global Standards

- **Unified CLI Interface**: Supports the standard DAG status tracking panel and `KeyboardInterrupt` graceful shutdown.
- macOS native notifications (`osascript`) on completion.
