# SKILL: smart-highlighter

## Purpose

Standalone Markdown annotation skill. Given any Markdown text, applies
`**bold**`, `==highlight==`, and `` `code` `` markup to key concepts via LLM.

Designed to be reusable across any upstream skill that produces Markdown output
(voice-memo, pdf-knowledge, web-clipper, etc.).

## Input Payload

```
markdown_text : str   — raw Markdown string (any length)
subject       : str   — optional subject label for config profile selection
```

## Output

Annotated Markdown string. The Anti-Tampering guard ensures the LLM can never
delete content: if the output is shorter than `verbatim_threshold × input length`,
the original chunk is returned unchanged.

## Anti-Tampering Guarantee

| Trigger | Behaviour |
|---|---|
| LLM output shorter than `verbatim_threshold` × input | Original chunk restored |
| LLM exception on any chunk | Original chunk restored, processing continues |

## Key Config Keys (`config/config.yaml`)

| Key | Purpose |
|---|---|
| `model` | Ollama model name |
| `chunk_size` | Max chars per LLM call |
| `verbatim_threshold` | Minimum output/input ratio (default 0.85) |
| `min_chunk_chars` | Skip LLM for very short chunks |

## Consumer Skills

| Caller | Phase | Input Source |
|---|---|---|
| `voice-memo` | P4 Highlight | `03_merged/<subject>/<lecture>.md` |
| `pdf-knowledge` | P2 Highlight | `01_Processed/<subject>/<pdf_id>/raw_extracted.md` |

## Version
- v1.0.0 — 2026-04-19: Extracted from voice-memo/p04 and pdf-knowledge/p02
