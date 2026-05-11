# academic_edu_assistant — Architecture

## Role

`academic_edu_assistant` is a **RAG-powered, cross-document comparison and flashcard generation skill**.
It reads multiple Markdown documents from a subject input directory, runs an LLM-powered comparative
analysis (Phase 1), then synthesizes the output into Anki-compatible CSV flashcards (Phase 2).

## Design Principles

1. **RAG over ChromaDB**: Uses `core.ai.hybrid_retriever` for semantic retrieval across the wiki vault.
2. **Multi-document Input**: Unlike other skills, does not operate on a single file — it scans all Markdown files in `data/academic_edu_assistant/input/<subject>/`.
3. **Strict Temperature = 0**: All comparison and flashcard generation calls enforce deterministic output.
4. **Phase Independence**: Phase 1 (compare) and Phase 2 (anki) are independently resumable via `StateManager`.

## Processing Flow

```
Input: data/academic_edu_assistant/input/<subject>/*.md
  │
  ├── Phase 1: Cross-Document Comparison (p01_compare.py)
  │     ├── Load all documents from input/<subject>/
  │     ├── Generate pairwise topic comparison matrix
  │     └── Output: data/academic_edu_assistant/output/01_comparison/<subject>/report.md
  │
  └── Phase 2: Anki Flashcard Generation (p02_anki.py)
        ├── Read comparison report (or raw input files)
        ├── Extract Q&A pairs via LLM
        └── Output: data/academic_edu_assistant/output/02_anki/<subject>/cards.csv
```

## Directory Structure

```
skills/academic_edu_assistant/
├── SKILL.md                          ← Quick-start guide
├── config/
│   ├── config.yaml                   ← Model profiles, chunk sizes, path definitions
│   └── prompt.md                     ← LLM prompts for comparison and flashcard generation
├── docs/
│   ├── ARCHITECTURE.md               ← This file
│   ├── PROJECT_RULES.md                     ← AI agent collaboration context
│   └── DECISIONS.md                  ← Technical decision log (ADRs)
└── scripts/
    ├── run_all.py                    ← Orchestrator: 2-phase runner with resume/interactive
    └── phases/
        ├── p00_rss_ingest.py         ← Phase 0: Optional RSS/web content ingestion
        ├── p01_compare.py            ← Phase 1: Cross-document comparison engine
        └── p02_anki.py               ← Phase 2: Anki CSV flashcard generator
```

## Data Flow

| Phase | Input | Output |
|:---|:---|:---|
| P0 (RSS Ingest) | RSS feed URL | `input/<subject>/*.md` |
| P1 (Compare) | `input/<subject>/*.md` | `output/01_comparison/<subject>/report.md` |
| P2 (Anki) | `output/01_comparison/<subject>/report.md` | `output/02_anki/<subject>/cards.csv` |

## CLI Commands

```bash
# Interactive mode — select subjects from menu
python3 skills/academic_edu_assistant/scripts/run_all.py

# Batch mode with specific query
python3 skills/academic_edu_assistant/scripts/run_all.py \
    --query "Compare Behaviorism vs Cognitivism" \
    --anki

# Force regeneration
python3 skills/academic_edu_assistant/scripts/run_all.py --force
```

## Dependencies

| Module | Purpose |
|:---|:---|
| `core.orchestration.pipeline_base.PipelineBase` | Base class for all phases |
| `core.ai.hybrid_retriever` | RAG retrieval over ChromaDB |
| `core.state.state_manager.StateManager` | Phase progress tracking |
| `core.utils.atomic_writer.AtomicWriter` | Corruption-safe file writes |
