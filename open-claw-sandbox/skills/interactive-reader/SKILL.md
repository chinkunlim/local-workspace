---
name: interactive-reader
description: "Interactive AI Reader. Allows users to write commands like `> [AI: ...]` inside Markdown files to get AI-generated inline context."
metadata:
  {
    "openclaw":
      {
        "emoji": "📖"
      }
  }
---

# Interactive Reader

**Open Claw Skill**

## Role & Purpose

The Interactive Reader enables you to collaborate with the AI directly inside your Markdown notes. It scans for special `> [AI: ...]` command tags, extracts the surrounding context, calls the LLM to generate a response (e.g., a summary, mind map, or explanation), and safely appends the result below the tag in-place.

## Usage

```bash
# Process a single file
python3 skills/interactive-reader/scripts/run_all.py --file "your_note.md"

# Batch process all notes (headless mode)
python3 skills/interactive-reader/scripts/run_all.py --process-all
```

## Tag Syntax

Insert the following tag anywhere inside a Markdown note:

```markdown
> [AI: Please explain the key concept in this paragraph]
```

After processing, the tag is marked as resolved to prevent re-processing:

```markdown
> [AI-DONE: Please explain the key concept in this paragraph]
> [AI-RESPONSE]
> ... the LLM response appears here ...
```

## Global Standards

- **Zero Temperature**: Enforces `temperature: 0` to guarantee precise, repeatable in-context annotations and eliminate hallucinations.
- **Headless CLI**: Supports `--process-all` and `--log-json` for full CI/CD compatibility.
- **Unified CLI Interface**: Supports standard Preflight Check, DAG status tracking panel, and interactive task selection.
- macOS native notifications (`osascript`) and graceful `KeyboardInterrupt` handling with checkpoint save.
