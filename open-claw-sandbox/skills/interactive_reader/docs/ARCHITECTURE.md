# interactive_reader — Architecture

## Role

`interactive_reader` is an **in-place AI annotation resolver**. It scans Markdown files
in the wiki vault for `> [AI: <instruction>]` marker blocks, generates contextually-aware
AI responses, and writes the answers inline below the marker — converting them to
`> [AI-DONE: <instruction>]`. This enables a human-in-the-loop, conversational annotation
workflow directly inside Obsidian notes.

## Design Principles

1. **In-place mutation**: Files are modified atomically using `AtomicWriter`. The original file is replaced with the annotated version in a single rename operation.
2. **Idempotency via `[AI-DONE:]` marker**: Already-processed markers are tagged `[AI-DONE:]` and skipped on re-runs. This ensures repeated execution is safe.
3. **Temperature = 0**: All LLM responses enforce deterministic output. Consistent answers across runs are essential for academic integrity.
4. **Context window**: The LLM is given the surrounding paragraph (before and after the marker) as context — not the entire document, to avoid context-window overflow.

## Processing Flow

```
Input: data/wiki/**/*.md (scanned recursively for [AI: ...] markers)
  │
  └── for each file containing [AI: ...] markers:
        ├── Extract marker + surrounding context (~1000 chars)
        ├── LLM generate response (temperature=0)
        ├── Inject response below marker
        ├── Convert [AI: ...] → [AI-DONE: ...]
        └── AtomicWriter.write(updated_content)
```

## AI Marker Syntax

| Marker | Meaning |
|:---|:---|
| `> [AI: <instruction>]` | Pending — will be processed on next run |
| `> [AI-DONE: <instruction>]` | Already processed — skipped on re-runs |

**Example in Obsidian note**:
```markdown
The Working Memory Model has three components.
> [AI: Summarize each component in one sentence]
```

**After processing**:
```markdown
The Working Memory Model has three components.
> [AI-DONE: Summarize each component in one sentence]

The **Central Executive** coordinates attention; the **Phonological Loop** handles verbal/auditory information; the **Visuospatial Sketchpad** processes visual and spatial data.
```

## Directory Structure

```
skills/interactive_reader/
├── SKILL.md              ← Quick-start guide
├── docs/
│   ├── ARCHITECTURE.md   ← This file
│   ├── CLAUDE.md         ← AI agent collaboration context
│   └── DECISIONS.md      ← Technical decision log
└── scripts/
    ├── run_all.py        ← Orchestrator: scans wiki, processes markers
    └── phases/
        └── p01_interactive.py  ← Phase 1: Marker resolution engine
```

## CLI Commands

```bash
# Process all pending markers across the entire wiki vault
python3 skills/interactive_reader/scripts/run_all.py --process-all

# Process a specific file
python3 skills/interactive_reader/scripts/run_all.py \
    --file data/wiki/Cognitive_Psychology/lecture_01.md
```

## Dependencies

| Module | Purpose |
|:---|:---|
| `core.orchestration.pipeline_base.PipelineBase` | Base class |
| `core.ai.llm_client.OllamaClient` | LLM inference (temperature=0) |
| `core.utils.atomic_writer.AtomicWriter` | In-place file mutation safety |
