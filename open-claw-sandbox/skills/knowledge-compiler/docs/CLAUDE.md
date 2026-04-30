# CLAUDE.md — Knowledge Compiler Skill

> AI agent collaboration context for the `knowledge-compiler` skill.
> Read this before making any changes to this skill or the wiki publishing logic.

## Skill Summary

`knowledge-compiler` is the final stage of the knowledge pipeline. It reads the outputs of
`audio-transcriber` and `doc-parser`, generates bidirectional `[[WikiLink]]` connections,
adds structured YAML front-matter, and publishes the results into `data/wiki/` — which is
simultaneously the user's Obsidian Vault.

## Key Invariants

1. **Never deletes wiki notes**: The compiler is additive only. Existing notes are updated (specific sections replaced) but never fully overwritten or deleted without `--force`.
2. **Reads, never re-processes**: This skill reads from other skills' `output/` directories. It does NOT re-run transcription, PDF parsing, or synthesis. It only compiles and links.
3. **Temperature = 0**: All link suggestion and synthesis is deterministic. Non-deterministic wiki compilation would cause links to shift on every run, breaking Obsidian's graph view.
4. **Glossary-driven linking**: `[[WikiLink]]` connections are generated based on shared terms from `core.utils.glossary_manager`. The glossary must be up-to-date for accurate cross-linking.
5. **Subject isolation**: Each subject's notes are compiled independently. A failure in one subject directory never blocks others.

## File Locations

| Item | Path |
|:---|:---|
| Config | `skills/knowledge-compiler/config/config.yaml` |
| LLM prompts | `skills/knowledge-compiler/config/prompt.md` |
| Orchestrator | `skills/knowledge-compiler/scripts/run_all.py` |
| Compile phase | `skills/knowledge-compiler/scripts/phases/p01_compile.py` |
| Graph phase | `skills/knowledge-compiler/scripts/phases/p02_extract_graph.py` |

## CLI Usage

```bash
# Interactive subject selection
python3 skills/knowledge-compiler/scripts/run_all.py

# Batch compilation — all pending subjects
python3 skills/knowledge-compiler/scripts/run_all.py --process-all

# Force re-compile and re-publish (overwrites existing wiki notes)
python3 skills/knowledge-compiler/scripts/run_all.py --force
```

## Common Agent Tasks

**Re-compile a specific subject after audio-transcriber updated its output**:
```bash
python3 skills/knowledge-compiler/scripts/run_all.py --subject "Cognitive Psychology" --force
```

**Rebuild the knowledge graph**:
```bash
python3 skills/knowledge-compiler/scripts/run_all.py --graph-only
```

## What NOT to Change Without Reading DECISIONS.md

- The additive-only wiki update strategy — overwriting could delete user annotations
- The `[[WikiLink]]` format — Obsidian requires double-bracket syntax
- YAML front-matter schema — `telegram-kb-agent`'s indexer depends on specific fields
- The glossary-driven link detection threshold — too low = noise links, too high = missed connections
