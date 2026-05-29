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
state_tracking:
  phases: ["p1", "p2"]
  labels:
    p1: "P1 (Map-Reduce)"
    p2: "P2 (Mermaid)"
io_contracts:
  consumes:
    - "text/markdown"
  produces:
    - "text/markdown"
---

# SKILL: note-generator

## Purpose

Standalone Markdown note synthesis skill. Given any text (typically an annotated
Markdown file), it generates a structured study note with a YAML header and an
optional Mermaid mindmap.

Designed to be reusable across any upstream skill that needs to condense long
texts into structured study materials.

## Quick Start

```bash
uv run skills/note_generator/scripts/run_all.py --process-all
```

## Input Payload

```
markdown_text : str   — raw text to synthesize (any length)
subject       : str   — optional subject label
label         : str   — optional document label (e.g., lecture name)
figure_list   : str   — optional list of figures/images for injection
```

**Eager Copy 機制 (樂觀執行) & 觸發控制**:
`note_generator` 會自動將 `smart_highlighter` 輸出的草稿預先拷貝至其 `inbox/` 產生預覽筆記。
然而，為了避免不必要的運算浪費，只有當 `04_final_verified` (經過 HITL 人工校對的最終文件) 存在時，它才會透過 EventBus 發送事件觸發下游的 `student_researcher` 與 `gemini_verifier_agent`。

## Output

A synthesized Markdown note including:
1. YAML frontmatter metadata (tokens used, generation time, chunks)
2. Main synthesized content
3. Mermaid diagram (automatically validated and retried if syntax fails)

## Map-Reduce Strategy

If the input length exceeds `chunk_threshold` (e.g., 6000 chars), the skill
automatically switches to a Map-Reduce strategy:
1. **Map**: Split input into chunks and extract key points from each.
2. **Reduce**: Combine all chunk summaries into a final unified note.

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
| `content_loss_threshold` | Guard: minimum output/input size ratio (e.g. 0.01) |

## Consumer Skills

| Caller | Phase | Input Source |
|---|---|---|
| `audio_transcriber` | P5 Synthesis | P4 Highlighted Markdown |
| `doc_parser` | P3 Synthesis | P2 Highlighted Markdown |

## Version

- v1.0.0 — 2026-04-19: Extracted from audio_transcriber/p05 and doc_parser/p03

## Global Standards

- **Unified CLI Interface**: Supports the standard DAG status tracking panel and `KeyboardInterrupt` graceful shutdown.
- macOS native notifications (`osascript`) on completion or error.
