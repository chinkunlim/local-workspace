# CLAUDE.md — Interactive Reader Skill

> AI agent collaboration context for the `interactive_reader` skill.
> Read this file before making any changes to this skill.

## Skill Summary

`interactive_reader` resolves `> [AI: <instruction>]` markers embedded in Obsidian Markdown notes.
It scans the wiki vault, generates contextually-aware AI responses, and writes the answers
inline — atomically replacing the marker with a `> [AI-DONE: ...]` tag and the generated content.

## Key Invariants

1. **Idempotency**: `[AI-DONE:]` markers are never processed again. This is critical — re-running must never duplicate or overwrite previously generated answers.
2. **Atomic writes**: All file updates use `AtomicWriter`. Never write directly to the wiki file with `open(path, 'w')` — a crash mid-write would corrupt the user's notes.
3. **Temperature = 0**: Non-negotiable. Academic annotation must be deterministic.
4. **Context window discipline**: Extract only the surrounding paragraph (~1000 characters around the marker), not the entire document. Large context windows cause LLM quality degradation for specific instructions.
5. **[AI-DONE:] marker must match [AI:] marker exactly**: The instruction text inside `[AI-DONE:]` must be identical to the original `[AI:]` text. This allows future tooling to link answers back to questions.

## File Locations

| Item | Path |
|:---|:---|
| Orchestrator | `skills/interactive_reader/scripts/run_all.py` |
| Resolution engine | `skills/interactive_reader/scripts/phases/p01_interactive.py` |
| Architecture doc | `skills/interactive_reader/docs/ARCHITECTURE.md` |

## CLI Usage

```bash
# Process all pending markers in the wiki vault
python3 skills/interactive_reader/scripts/run_all.py --process-all

# Process a single specific file
python3 skills/interactive_reader/scripts/run_all.py \
    --file data/wiki/Cognitive_Psychology/lecture_01.md
```

## Common Agent Tasks

**Debugging a marker that wasn't processed**: Check that the marker uses the exact syntax
`> [AI: ...]` (with the `>` blockquote prefix). Missing the `>` means it will not be detected.

**Resetting a processed marker**: Manually change `[AI-DONE: ...]` back to `[AI: ...]` in the
file. The next run will re-process it.

## What NOT to Change Without Reading DECISIONS.md

- The `[AI-DONE:]` idempotency mechanism — its exact string format is matched by regex
- The context window size (~1000 chars) — calibrated to avoid token overflow with instructions
- `temperature: 0` — must remain locked for deterministic academic output
- `AtomicWriter` usage — any direct file write breaks the corruption-safety guarantee
