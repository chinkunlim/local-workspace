# knowledge-compiler — Architecture

## Role

`knowledge-compiler` is the **knowledge publishing and bidirectional linking engine**.
It scans the final outputs of factory skills (`audio-transcriber`, `doc-parser`) and
synthesizes them into a unified, interlinked Obsidian wiki vault at `data/wiki/`.
It is the bridge between raw pipeline outputs and the human-readable knowledge base.

## Design Principles

1. **Publisher, not producer**: `knowledge-compiler` reads from other skills' outputs. It does NOT re-run or duplicate any processing.
2. **Bidirectional `[[linking]]`**: Generates Obsidian `[[WikiLink]]` connections between related notes based on shared terminology and topic overlap.
3. **Temperature = 0**: All linking and synthesis calls enforce deterministic output.
4. **Additive only**: Never deletes existing wiki notes. New notes are published; existing notes are updated by appending or replacing specific sections.

## Processing Flow

```
Input sources:
  ├── data/audio-transcriber/output/03_merged/<subject>/*.md
  └── data/doc-parser/output/05_Final_Knowledge/<subject>/<pdf_id>/content.md
  │
  └── Phase 1: Compile (p01_compile.py)
        ├── Load all final outputs from both skill trees
        ├── Detect shared terms across documents (glossary_manager)
        ├── Generate [[WikiLink]] connections
        ├── Build YAML front-matter (title, subject, source, date)
        └── Publish to data/wiki/<subject>/<note_name>.md (AtomicWriter)

  Optional Phase 2: Graph Extraction (p02_extract_graph.py)
        ├── Build a knowledge graph from wiki links
        └── Output: data/wiki/_graph/graph.json
```

## Directory Structure

```
skills/knowledge-compiler/
├── SKILL.md              ← Quick-start guide
├── config/
│   ├── config.yaml       ← Model profiles, link detection thresholds
│   └── prompt.md         ← LLM prompts for link suggestion and synthesis
├── docs/
│   ├── ARCHITECTURE.md   ← This file
│   ├── CLAUDE.md         ← AI agent collaboration context
│   └── DECISIONS.md      ← Technical decision log
└── scripts/
    ├── run_all.py        ← Orchestrator: scans outputs, publishes to wiki
    └── phases/
        ├── p01_compile.py          ← Phase 1: Core compilation and publishing
        └── p02_extract_graph.py    ← Phase 2: Knowledge graph extraction
```

## Output Structure (`data/wiki/`)

```
data/wiki/
└── <Subject>/
    ├── <note_name>.md           ← Published note with YAML front-matter + [[links]]
    └── _graph/
        └── graph.json           ← Knowledge graph (optional, Phase 2)
```

## CLI Commands

```bash
# Interactive compilation — select subjects from menu
python3 skills/knowledge-compiler/scripts/run_all.py

# Headless batch compilation — all subjects
python3 skills/knowledge-compiler/scripts/run_all.py --process-all

# Force re-publish (overwrites existing wiki notes)
python3 skills/knowledge-compiler/scripts/run_all.py --force
```

## Dependencies

| Module | Purpose |
|:---|:---|
| `core.orchestration.pipeline_base.PipelineBase` | Base class |
| `core.utils.glossary_manager` | Shared terminology detection for linking |
| `core.utils.atomic_writer.AtomicWriter` | Corruption-safe wiki publishing |
| `core.utils.knowledge_pusher` | Output routing to `data/wiki/` |
