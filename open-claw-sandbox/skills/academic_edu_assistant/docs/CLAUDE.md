# CLAUDE.md — Academic & Education Assistant Skill

> AI agent collaboration context for the `academic_edu_assistant` skill.
> Read this file in full before making any code changes to this skill.

## Skill Summary

`academic_edu_assistant` is a **RAG-powered cross-document comparison engine and Anki flashcard generator**.
It reads multiple Markdown documents from a subject directory, performs pairwise comparative analysis
(Phase 1), and synthesizes the results into Anki-compatible CSV flashcards (Phase 2). It optionally
supports RSS/web content ingestion (Phase 0) to enrich the comparison corpus.

## Current State (2026-04-30)

- **Status**: Production
- **Model in use**: `gemma3:12b` (Ollama) via `core.ai.llm_client.OllamaClient`
- **RAG Backend**: ChromaDB via `core.ai.hybrid_retriever`
- **Architecture version**: V2.0 (RAG integration, RSS ingest, P2 Anki CSV)

## Key Invariants

1. **Multi-document input required**: P1 needs at least 2 Markdown documents in `input/<subject>/` to perform comparison. Single-file runs produce a self-analysis report, not a comparison.
2. **Phase sequencing enforced**: P2 (Anki) requires P1 (comparison report) to exist. `StateManager` enforces this dependency.
3. **Temperature = 0 for all phases**: Comparison analysis and flashcard generation must be deterministic. Never increase temperature.
4. **CSV output format is strict**: P2 output must conform to Anki's expected CSV schema (Front, Back, Tags). Any deviation breaks Anki import.
5. **State tracking per subject**: Each subject directory maintains independent `StateManager` progress. A failure in one subject does not affect others.

## File Locations

| Item | Path |
|:---|:---|
| Config | `skills/academic_edu_assistant/config/config.yaml` |
| LLM prompts | `skills/academic_edu_assistant/config/prompt.md` |
| Orchestrator | `skills/academic_edu_assistant/scripts/run_all.py` |
| Comparison phase | `skills/academic_edu_assistant/scripts/phases/p01_compare.py` |
| Anki phase | `skills/academic_edu_assistant/scripts/phases/p02_anki.py` |
| Architecture doc | `skills/academic_edu_assistant/docs/ARCHITECTURE.md` |

## CLI Usage

```bash
# Interactive subject selection
python3 skills/academic_edu_assistant/scripts/run_all.py

# Direct comparison with Anki output
python3 skills/academic_edu_assistant/scripts/run_all.py \
    --query "Compare core assumptions of Behaviorism and Cognitivism" \
    --anki

# Force full regeneration of all phases
python3 skills/academic_edu_assistant/scripts/run_all.py --force
```

## Placing Input Files

Drop Markdown files into the subject directory before running:
```bash
# Example: comparing two psychology papers
cp paper_behaviorism.md data/academic_edu_assistant/input/Psychology/
cp paper_cognitivism.md data/academic_edu_assistant/input/Psychology/
python3 skills/academic_edu_assistant/scripts/run_all.py
```

## What NOT to Change Without Reading DECISIONS.md

- The Anki CSV column schema (Front, Back, Tags) — Anki import breaks on deviation
- The `max_documents_per_comparison` limit — higher values cause OOM on 16GB hardware
- Temperature settings — determinism is critical for reproducible study cards
- The pairwise comparison loop in P1 — it handles O(n²) document combinations efficiently
