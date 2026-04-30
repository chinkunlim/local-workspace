---
name: knowledge-compiler
description: "Knowledge Base Compiler. Analyzes and links all markdown outputs to generate bidirectional wiki notes."
metadata:
  {
    "openclaw":
      {
        "emoji": "🧠"
      }
  }
---

# Knowledge Compiler

> **Pipeline**: Scans `doc-parser` and `audio-transcriber` outputs → Links concepts → Publishes to `data/wiki/`

## Quick Start

```bash
# Interactive mode
python3 skills/knowledge-compiler/scripts/run_all.py

# Headless batch mode
python3 skills/knowledge-compiler/scripts/run_all.py --process-all

# Force full re-compile
python3 skills/knowledge-compiler/scripts/run_all.py --force
```

## Core Protections (V2.0 Antigravity)

- **Zero Temperature**: `config/config.yaml` enforces `temperature: 0` to guarantee 100% deterministic knowledge compilation and eliminate LLM semantic drift.
- **Headless CLI**: Supports `--process-all` and `--log-json` for full CI/CD infrastructure compatibility.

## Global Standards

- **Unified CLI Interface**: All run scripts implement three standard mechanisms:
  1. **Preflight Check**: Validates all dependencies and configuration before processing.
  2. **DAG Status Tracking Panel**: Real-time visualisation of pipeline progress.
  3. **Interactive Task Selection**: Dynamically select PENDING or COMPLETED tasks for re-run.
- macOS native notifications (`osascript`) and graceful `KeyboardInterrupt` handling with checkpoint save.
