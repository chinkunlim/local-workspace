# CLAUDE.md — Note Generator Skill

> AI agent collaboration context for the `note_generator` skill.
> Read this file in full before making any code changes to this skill.

## Skill Summary

`note_generator` is a **stateless, Map-Reduce synthesis skill**. It receives a raw Markdown
string and returns a structured academic study note — complete with a YAML front-matter header
and a Mermaid mind-map. It is a **Secondary Processing Skill**: it does NOT own any data
directories and performs NO file I/O of its own. All data routing, `AtomicWriter` calls, and
`StateManager` updates are the exclusive responsibility of the calling orchestrator.

## Current State (2026-04-30)

- **Status**: Production
- **Model in use**: `gemma3:12b` (Ollama) via `core.ai.llm_client.OllamaClient`
- **Active consumers**: `audio_transcriber` Phase 3 (post-merge), `doc_parser` final synthesis
- **Architecture version**: V2.0 (Map-Reduce, Agentic Mermaid Retry, Content-Loss Guard)

## Key Invariants

1. **Stateless by design**: `NoteGenerator().run(...)` accepts a `str` and returns a `str`. No file system access.
2. **Map-Reduce for large inputs**: If `len(text) > chunk_threshold`, the skill automatically switches to a multi-step map-then-reduce flow. Do NOT disable this — it is the sole mechanism preventing LLM context-window overflow.
3. **Content-Loss Guard is non-negotiable**: If the output retention ratio falls below `content_loss_threshold` (default `0.01`), the result is rejected and a `ValueError` is raised. Never lower this below `0.01` without extensive testing.
4. **Agentic Mermaid Retry**: The skill includes an internal retry loop to repair syntactically invalid Mermaid diagrams. Do not remove or bypass this — callers expect valid Mermaid output.
5. **Temperature = 0 for Reduce pass**: The final consolidation/reduce prompt uses `temperature: 0` for deterministic output. Only the Map pass uses a slightly higher value (`0.1–0.2`).

## Architecture

```
Input: markdown_text (str), subject, label, figure_list
  │
  ├── if len(text) > chunk_threshold:  Map-Reduce Flow
  │     ├── smart_split(text, map_chunk_size)
  │     ├── Map: LLM summarizes each chunk independently
  │     └── Reduce: LLM synthesizes all summaries into final note
  │
  └── else: Standard Flow
        └── LLM synthesizes text directly
              │
              ├── Agentic Mermaid Check & Retry Loop
              └── Output: Structured Markdown note (str)
```

## File Locations

| Item | Path |
|:---|:---|
| Config | `skills/note_generator/config/config.yaml` |
| LLM prompts | `skills/note_generator/config/prompt.md` |
| Orchestrator | `skills/note_generator/scripts/synthesize.py` |
| Architecture doc | `skills/note_generator/docs/ARCHITECTURE.md` |

## CLI Usage

```bash
# Run standalone synthesis (called by orchestrators, not usually run directly)
python3 skills/note_generator/scripts/synthesize.py \
    --subject "Cognitive Psychology" \
    --label "lecture_01" \
    --input-file data/wiki/Cognitive_Psychology/lecture_01.md \
    --output-file data/wiki/Cognitive_Psychology/lecture_01_summary.md
```

## Integration Pattern

```python
from skills.note_generator.scripts.synthesize import NoteGenerator

final_note = NoteGenerator().run(
    markdown_text=full_text,
    subject="Physics",
    label="Lecture-01",
    figure_list="- Fig 1: Schema",
    profile="reasoning"  # optional: selects config profile
)
```

## Common Agent Tasks

**Switching models**: Edit `config/config.yaml` → `active_profile`, or run:
```bash
python3 core/cli/cli_config_wizard.py --skill note_generator
```

**Adjusting chunk size**: Edit `config.yaml` → `chunking.map_chunk_size`. Do NOT go above 4000
characters without RAM profiling — `gemma3:12b` can OOM on large context windows.

**Debugging a synthesis failure**: Check the `ValueError` message from `Content-Loss Guard`.
If the ratio is < threshold, the LLM produced an excessively short output. Try lowering the
temperature or switching to a reasoning model profile.

## What NOT to Change Without Reading DECISIONS.md

- `content_loss_threshold` — calibrated to reject LLM laziness without being too strict
- `verbatim_threshold` in the anti-tampering guard — ensures the LLM actually adds value
- The Map-Reduce chunk boundary logic — overlapping boundaries prevent mid-sentence splits
- `max_retries` in the Mermaid retry loop — higher values cause infinite loops on broken prompts
