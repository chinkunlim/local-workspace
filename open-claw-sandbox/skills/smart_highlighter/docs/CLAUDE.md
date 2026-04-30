# CLAUDE.md — Smart Highlighter Skill

> AI agent collaboration context for the `smart_highlighter` skill.
> Read this file in full before making any code changes to this skill.

## Skill Summary

`smart_highlighter` is a **stateless, anti-tampering annotation skill**. It receives a raw
Markdown string and returns the same Markdown string with AI-injected `==highlighted==` markers
on key academic terms, definitions, and critical passages. It is a **Secondary Processing Skill**:
it does NOT own data directories, performs NO file I/O, and manages NO state. The calling
orchestrator owns all of those responsibilities.

## Current State (2026-04-30)

- **Status**: Production
- **Model in use**: `gemma3:12b` (Ollama) via `core.ai.llm_client.OllamaClient`
- **Active consumers**: Called by `audio-transcriber` post-merge orchestrator (formerly Phase 4)
- **Architecture version**: V2.0 (Anti-Tampering Guard, Chunked by default)

## Key Invariants

1. **Stateless by design**: `SmartHighlighter().run(...)` accepts a `str` and returns a `str`. Zero filesystem access.
2. **Anti-Tampering Guard is non-negotiable**: If the LLM returns a substantially shorter output (`len(output) < len(input) * verbatim_threshold`), the original chunk is restored. This prevents the LLM from "helpfully" summarizing text instead of annotating it. **Never lower `verbatim_threshold` below 0.75.**
3. **Exception isolation**: If any chunk fails (LLM error, timeout), that chunk is restored from the original and processing continues on the next chunk. A single bad chunk must never abort the entire document.
4. **Temperature = 0**: Highlighting must be deterministic and reproducible. Never increase temperature for this skill.
5. **Caller owns state**: `StateManager` updates, `AtomicWriter` calls, and path resolution stay in the calling orchestrator.

## Architecture

```
Input: markdown_text (str)
  │
  ├── smart_split(text, chunk_size)      # boundary-aware chunking
  │     │
  │     └── for each chunk:
  │           ├── LLM annotate chunk (temperature=0)
  │           ├── Anti-Tampering Guard
  │           │     └── if len(output) < len(chunk) * verbatim_threshold:
  │           │           → restore original chunk
  │           └── on exception → restore original chunk
  │
  └── Output: joined annotated Markdown (str)
```

## File Locations

| Item | Path |
|:---|:---|
| Config | `skills/smart_highlighter/config/config.yaml` |
| LLM prompts | `skills/smart_highlighter/config/prompt.md` |
| Main script | `skills/smart_highlighter/scripts/highlight.py` |
| Architecture doc | `skills/smart_highlighter/docs/ARCHITECTURE.md` |

## CLI Usage

```bash
# Highlight a single Markdown file
python3 skills/smart_highlighter/scripts/highlight.py \
    --input-file data/wiki/Cognitive_Psychology/lecture_01.md \
    --output-file data/wiki/Cognitive_Psychology/lecture_01_highlighted.md
```

## Integration Pattern

```python
from skills.smart_highlighter.scripts.highlight import SmartHighlighter

annotated_text = SmartHighlighter().run(
    markdown_text=full_text,
    subject="Physics",      # optional: selects subject-specific config profile
    profile="strict",       # optional: override active_profile in config.yaml
)
```

## Common Agent Tasks

**Switching models**: Edit `config/config.yaml` → `active_profile`, or run:
```bash
python3 core/cli/cli_config_wizard.py --skill smart_highlighter
```

**Adjusting highlight aggressiveness**: Edit `config/prompt.md`. Be conservative —
over-highlighting defeats the purpose. The prompt already constrains annotation to:
key terms, definitions, critical thresholds, and important dates/names.

**Debugging a tampered output**: If the Anti-Tampering Guard fires repeatedly, check:
1. The prompt in `config/prompt.md` — ensure it says "annotate only, do not rephrase"
2. The model size — smaller models (e.g., `phi3`) tend to summarize instead of annotate
3. `chunk_size` in `config.yaml` — too-large chunks overwhelm the model's instruction-following

## What NOT to Change Without Reading DECISIONS.md

- `verbatim_threshold` — core anti-tamper protection; 0.85 is carefully calibrated
- The exception-recovery behavior (restore original chunk on error) — it's a deliberate safety net
- `temperature: 0` in config — determinism is essential for idempotent re-runs
- The chunking strategy — `smart_split` boundary detection prevents mid-sentence annotation breaks
