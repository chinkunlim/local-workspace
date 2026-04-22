---
name: inbox-manager
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
python skills/inbox-manager/scripts/query.py --list

# Add a new audio_ref pattern
python skills/inbox-manager/scripts/query.py --add "_ppt" --routing audio_ref --description "PowerPoint slides"

# Add a 'both' pattern (doc-parser + audio ref)
python skills/inbox-manager/scripts/query.py --add "_units" --routing both --description "Course units"

# Remove a pattern
python skills/inbox-manager/scripts/query.py --remove "_ppt"
```

## Routing Modes

| Mode | Behaviour |
|---|---|
| `audio_ref` | PDF sent to audio-transcriber as proofreading reference |
| `doc_parser` | PDF sent to doc-parser for full Markdown parsing |
| `both` | PDF copied to BOTH destinations simultaneously |

## 全域標準化

- **全域標準化介面 (Global Standardization)**: 採用統一的 CLI 狀態與 DAG 追蹤面板，支援 macOS 原生系統通知 (osascript)，並具備 `KeyboardInterrupt` 優雅中斷保護。
