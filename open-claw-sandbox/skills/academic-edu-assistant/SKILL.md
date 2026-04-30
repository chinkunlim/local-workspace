---
name: academic-edu-assistant
description: "Academic & Education Assistant. RAG-based cross-comparison engine and Anki flashcard generator."
metadata:
  {
    "openclaw":
      {
        "emoji": "🎓"
      }
  }
---

# Academic & Education Assistant

**Open Claw Skill**

## Role & Purpose

Designed for deep learning, research, and exam preparation. Performs cross-document comparison across multiple notes and automatically generates Anki flashcards ready for import.

## Pipeline Phases

1. **Phase 1: Cross-Comparison (`p01_compare.py`)**: Reads multiple documents from `input/<subject>/`, performs comparative analysis, and outputs a consolidated comparison report to `01_comparison/`.
2. **Phase 2: Anki Flashcards (`p02_anki.py`)**: Reads the comparison report or source notes and distils them into a CSV file directly importable into Anki.

## Usage

Place the Markdown files you want to compare into:
```
data/academic-edu-assistant/input/<YourSubjectName>/
```

Then run:
```bash
python3 skills/academic-edu-assistant/scripts/run_all.py
```

## Global Standards

- **Unified CLI Interface**: Supports standard Preflight Check, DAG status tracking panel, and interactive task re-run selection.
- macOS native notifications (`osascript`) and graceful `KeyboardInterrupt` handling with checkpoint save.
- **Zero Temperature**: Enforces `temperature: 0` to guarantee deterministic, repeatable comparison results.
