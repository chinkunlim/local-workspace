# NoteGenerator — Architecture

## Role

`note-generator` is a **stateless synthesis skill**. It receives a long Markdown
string and returns a summarized, structured study note with a YAML header and a
Mermaid mindmap. It does not own data directories; all file I/O is managed by the caller.

## Design Principles

1. **Single Responsibility**: synthesize text into structured notes
2. **Context-Aware Scaling**: automatically switches to Map-Reduce for large inputs
3. **Self-Healing Output**: Agentic retry loop for brittle formats (Mermaid)
4. **Content-Loss Guard**: aborts if output retention ratio falls below threshold

## Processing Flow

```
Input: markdown_text (str), subject, label, figure_list
  │
  ├── if len(text) > chunk_threshold:
  │     ├── Map-Reduce Flow
  │     │     ├── smart_split(text, map_chunk_size)
  │     │     ├── Map: summarize each chunk
  │     │     └── Reduce: synthesize all chunk summaries into final note
  │     │
  └── else:
        ├── Standard Flow
        └── Synthesize directly into final note
              │
              ├── Agentic Mermaid Check
              │     ├── Validate Mermaid syntax
              │     └── if invalid → retry LLM generation with error feedback
              │
              └── Output: Synthesized Markdown note (str) with YAML header
```

## Content-Loss Guard

```
retention_ratio = len(output) / len(input)

if retention_ratio < content_loss_threshold (e.g. 0.01):
    → raise ValueError("Note retention ratio too low (LLM truncation/laziness)")
```

## Agentic Mermaid Retry Loop

```python
def _agentic_mermaid_retry(text):
    errors = validate_mermaid_syntax(text)
    if not errors: return text

    for attempt in range(max_retries):
        prompt = f"Fix these errors: {errors}\n\nLast output:\n{text}"
        text = LLM.generate(prompt)
        errors = validate_mermaid_syntax(text)
        if not errors: break

    return text
```

## Integration Pattern

Callers import `NoteGenerator` directly:

```python
from skills.note_generator.scripts.synthesize import NoteGenerator

final_note = NoteGenerator().run(
    markdown_text=full_text,
    subject="Physics",
    label="Lecture-01",
    figure_list="- Fig 1: Schema",
    profile="reasoning"
)
```

## Dependencies

| Module | Purpose |
|---|---|
| `core.PipelineBase` | Base class: config, LLM client, logging, spinners |
| `core.text_utils.smart_split` | Context-aware text chunking |
| `core.OllamaClient` | LLM inference |
