---
name: smart_highlighter
description: Non-destructively annotate any Markdown text with bold, highlight, and
  code markup using an LLM, with an Anti-Tampering verbatim guard to prevent content
  loss.
metadata:
  openclaw:
    emoji: 🖊️
    display_name: 智能高亮
state_tracking:
  phases:
  - p1
  labels:
    p1: P1 (Highlight)
io_contracts:
  consumes:
  - text/markdown
  produces:
  - text/markdown
---

# SKILL: smart_highlighter

## Purpose

Standalone Markdown annotation skill. Given any Markdown text, applies
`**bold**`, `==highlight==`, and `` `code` `` markup to key concepts via LLM.

Designed to be reusable across any upstream skill that produces Markdown output
(audio_transcriber, doc_parser, web-clipper, etc.).

## Quick Start

```bash
uv run skills/smart_highlighter/scripts/run_all.py --process-all
```

## Input Payload

```
markdown_text : str   — raw Markdown string (any length)
subject       : str   — optional subject label for config profile selection
```

**Eager Copy 機制 (樂觀執行)**:
`smart_highlighter` 會自動將 `proofreader` 輸出的 `03_doc_completeness` 草稿預先拷貝至其 `inbox/` 執行高亮。當 `proofreader` 完成 HITL 並產生 `04_final_verified` 時，它會自動將草稿覆寫並重新產生最終的螢光筆版本。

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
| `audio_transcriber` | P4 Highlight | `03_merged/<subject>/<lecture>.md` |
| `doc_parser` | P2 Highlight | `01_Processed/<subject>/<pdf_id>/raw_extracted.md` |

## Version

- v1.0.0 — 2026-04-19: Extracted from audio_transcriber/p04 and doc_parser/p02

## Global Standards

- **Unified CLI Interface**: Supports the standard DAG status tracking panel and `KeyboardInterrupt` graceful shutdown.
- macOS native notifications (`osascript`) on completion or error.
