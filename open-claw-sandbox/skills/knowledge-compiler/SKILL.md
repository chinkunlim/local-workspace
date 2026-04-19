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

# Knowledge Compiler (知識庫編譯器)

> **Pipeline**: Scans `doc-parser` and `audio-transcriber` outputs → Links concepts → Generates `data/wiki` Markdown

## Quick Start

```bash
python3 skills/knowledge-compiler/scripts/run_all.py
```
