# DECISIONS.md — Smart Highlighter Skill

> Technical decision log. Every non-obvious architectural choice is recorded here
> with date, context, and rationale. Future developers must read the relevant entry
> before changing anything governed by that decision.

---

## 2026-04-20 — Anti-Tampering Guard (verbatim_threshold = 0.85)

**Decision**: After each LLM annotation call, verify that `len(output.strip()) >= len(chunk) * verbatim_threshold`. If the output is shorter, discard it and restore the original chunk.

**Context**: Early testing revealed that smaller LLMs (and occasionally `gemma3:12b` under high context load) would interpret the highlight instruction as a summarization instruction, returning a much shorter "improved" version of the text. This silently destroys original content.

**Chosen approach**: `verbatim_threshold = 0.85` means the LLM output must be at least 85% the length of the input chunk. The `==highlight==` markers add characters, so legitimate outputs will always be ≥100% the input length. The 85% threshold provides a safety margin for minor rewording.

**Trade-off**: An LLM that correctly follows instructions will never trigger this guard.
If it fires frequently, the problem is in the prompt or model selection, not the threshold.
**Never lower below 0.75** — that would allow significant content deletion to pass through.

---

## 2026-04-19 — Extraction of Highlighting from `audio-transcriber` and `doc-parser`

**Decision**: Remove Phase 4 (highlight) from `audio-transcriber` and Phase 2 (highlight) from `doc-parser`. Create `smart_highlighter` as a standalone, reusable annotation skill.

**Context**: Both extraction skills contained duplicated highlighting prompts and logic.
Any update to the highlighting approach required editing two separate skills — a classic
Single Responsibility violation.

**Chosen approach**: `SmartHighlighter` is a standalone class importable by any orchestrator:
```python
from skills.smart_highlighter.scripts.highlight import SmartHighlighter
```
The calling skill passes raw text and receives annotated text. Zero duplication.

**Impact**: Highlighting logic is now maintained in a single location.
All skills that need annotation import `SmartHighlighter` directly.

---

## 2026-04-19 — Exception Isolation Per Chunk

**Decision**: If any chunk processing fails (LLM timeout, API error, JSON parse error),
catch the exception, log it at `WARNING` level, and restore the original chunk.
Processing continues on the next chunk without aborting.

**Context**: A transient Ollama timeout on chunk 3 of 20 should NOT destroy the
annotation of chunks 1–2 and 4–20. Silent partial failures are worse than slow runs.

**Chosen approach**: Each chunk is wrapped in an individual `try/except` block.
On exception: log `warning`, append original chunk to output list, increment failure counter.
After all chunks: if `failure_count > 0`, log `error` summarizing total failures.

**Trade-off**: The caller receives a partially annotated document with `failure_count > 0`
rather than a complete failure. The caller is responsible for deciding whether partial
annotation is acceptable (usually yes — original text is preserved).

---

## 2026-04-15 — Chunked Processing by Default (Never Single-Pass)

**Decision**: Always chunk the input via `core.utils.text_utils.smart_split()`, even for
short documents. Never attempt single-pass annotation of the entire document.

**Context**: Testing showed that `gemma3:12b` loses annotation quality for documents
exceeding ~2,000 tokens. It tends to annotate only the beginning of long documents
and produce minimal highlights in the second half.

**Chosen approach**: `smart_split()` uses a `chunk_size=3000` characters with a
`overlap=100` characters boundary buffer. Even a 500-character document is split into
one chunk (no overhead). `chunk_size` is configurable in `config.yaml`.

**Trade-off**: More LLM calls for long documents. Accepted — annotation quality is
the non-negotiable priority.

---

## 2026-04-30 — Temperature Locked to 0

**Decision**: `temperature: 0` is hardcoded in the active config profile for all annotation
calls. It is not configurable per-invocation.

**Context**: Highlighting must be reproducible. If the same document produces different
highlights on each run, it undermines the user's ability to trust the system's output
and breaks idempotency checks in the `StateManager`.

**Trade-off**: Deterministic output may occasionally miss creative connections that a higher
temperature might surface. Accepted — for academic annotation, precision beats creativity.
