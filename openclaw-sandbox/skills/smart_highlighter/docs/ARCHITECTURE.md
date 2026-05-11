# SmartHighlighter — Architecture

## Role

`smart-highlighter` is a **stateless annotation skill**. It receives a Markdown
string and returns a Markdown string — nothing more. It owns no data directories
of its own during normal operation; all path management stays in the caller.

## Design Principles

1. **Single Responsibility**: annotate text, nothing else
2. **Anti-Tampering by design**: verbatim_threshold guard is non-negotiable
3. **Caller owns state**: `StateManager`, paths, and `AtomicWriter` stay in caller
4. **Chunked by default**: uses `core.text_utils.smart_split` for any input size

## Processing Flow

```
Input: markdown_text (str)
  │
  ├── smart_split(text, chunk_size)
  │     │
  │     └── for each chunk:
  │           ├── LLM annotate (via core.OllamaClient)
  │           ├── verbatim_threshold guard
  │           │     └── if output too short → restore original chunk
  │           └── on exception → restore original chunk
  │
  └── Output: joined annotated Markdown (str)
```

## Anti-Tampering Guard

```
verbatim_threshold = 0.85  (configurable)

if len(output.strip()) < len(chunk) * verbatim_threshold:
    → restore original chunk (LLM output discarded)
```

## Integration Pattern

Callers import `SmartHighlighter` directly:

```python
from skills.smart_highlighter.scripts.highlight import SmartHighlighter

annotated = SmartHighlighter().run(
    markdown_text=full_text,
    subject="Physics",       # optional: selects config profile
    profile="strict",        # optional: override active_profile
)
```

## Dependencies

| Module | Purpose |
|---|---|
| `core.PipelineBase` | Base class: config, LLM client, logging, signal handling |
| `core.text_utils.smart_split` | Context-aware text chunking |
| `core.OllamaClient` | LLM inference |

## What It Does NOT Own

- Data paths (`self.dirs` is unused externally — callers pass raw text)
- StateManager updates
- AtomicWriter calls
- Phase sequencing
