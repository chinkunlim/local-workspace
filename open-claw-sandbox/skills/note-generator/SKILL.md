---
name: note-generator
description: Synthesize any Markdown input into structured study notes with a YAML header and Mermaid mindmap, using a Map-Reduce strategy for large texts and an agentic retry loop for self-healing Mermaid syntax.
metadata:
  {
    "openclaw":
      {
        "emoji": "📝"
      }
  }
---

# SKILL: note-generator

## Purpose

Standalone Markdown note synthesis skill. Given any text (typically an annotated
Markdown file), it generates a structured study note with a YAML header and an
optional Mermaid mindmap.

Designed to be reusable across any upstream skill that needs to condense long
texts into structured study materials.

## Input Payload

```
markdown_text : str   — raw text to synthesize (any length)
subject       : str   — optional subject label
label         : str   — optional document label (e.g., lecture name)
figure_list   : str   — optional list of figures/images for injection
```

## Output

A synthesized Markdown note including:
1. YAML frontmatter metadata (tokens used, generation time, chunks)
2. Main synthesized content
3. Mermaid diagram (automatically validated and retried if syntax fails)

## Map-Reduce Strategy

If the input length exceeds `chunk_threshold` (e.g., 6000 chars), the skill
automatically falls back to a Map-Reduce strategy:
1. **Map**: split input into chunks, run `Phase 5 Part A: 分塊摘要提取指令` on each.
2. **Reduce**: combine all chunk summaries, run `Phase 5: 筆記合成指令`.

## Agentic Mermaid Retry

Mermaid syntax is often brittle. If the generated output contains invalid or
incomplete Mermaid `mindmap` syntax, the skill automatically feeds the error back
to the LLM and asks it to correct the code (up to `mermaid_retry_max` times).

## Key Config Keys (`config/config.yaml`)

| Key | Purpose |
|---|---|
| `model` | Ollama model name |
| `chunk_threshold` | Max input size before switching to Map-Reduce |
| `map_chunk_size` | Size of chunks during the Map phase |
| `mermaid_retry_max` | Maximum LLM correction loops for broken Mermaid syntax |
| `content_loss_threshold`| Guard: minimum output/input size ratio (e.g. 0.01) |

## Consumer Skills

| Caller | Phase | Input Source |
|---|---|---|
| `audio-transcriber` | P5 Synthesis | P4 Highlighted Markdown |
| `doc-parser` | P3 Synthesis | P2 Highlighted Markdown |

## Version
- v1.0.0 — 2026-04-19: Extracted from audio-transcriber/p05 and doc-parser/p03
