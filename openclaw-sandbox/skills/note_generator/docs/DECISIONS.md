# DECISIONS.md — Note Generator Skill

> Technical decision log. Every non-obvious architectural choice is recorded here
> with date, context, and rationale. Future developers must read the relevant entry
> before changing anything governed by that decision.

---

## 2026-05-04 — Quality-First Model Profile: `qwen3_reasoning` (qwen3:14b)

**Decision**: Switched `active_profile` from `phi4_reasoning` to `qwen3_reasoning`, using
`qwen3:14b` as the primary synthesis model.

**Context**: Performance profiling under the quality-first strategy (ADR-009) showed that
`phi4-mini-reasoning` (3.8B), while fast and 128K-context capable, produces lower-quality
Cornell notes and Mermaid diagrams compared to the 14B `qwen3:14b` model. Since the
TaskQueue ensures sequential single-threaded execution, there is no OOM risk from using
the larger model.

**Profile Parameters**:
- `model`: `qwen3:14b`
- `chunk_threshold`: 6000 (smaller than phi4's 8000 to account for 14B overhead)
- `map_chunk_size`: 5000
- `num_ctx`: 32768 (conservative cap for 16GB RAM)
- `temperature`: 0.1
- `mermaid_retry_max`: 3 (increased from 2 for better diagram reliability)

**Fallback**: `phi4_reasoning` profile retained. Switch via `synthesize.active_profile: phi4_reasoning`.

---

## 2026-04-?? — phi4_reasoning Profile: `phi4-mini-reasoning`

**Decision**: Added `phi4_reasoning` profile using `phi4-mini-reasoning` as a synthesis alternative
to `deepseek-r1:14b`. Now serves as the official fallback profile.

**Context**: `phi4-mini-reasoning` (3.8B) with a 128K context window allows larger chunks
(`chunk_threshold: 8000`), reducing Map-Reduce splits for long transcripts and improving
speed with lower VRAM usage.

---


**Decision**: For inputs exceeding `chunk_threshold` characters, split the input into chunks,
summarize each independently (Map), then synthesize all summaries into a final note (Reduce).

**Context**: Early testing with single-pass synthesis on a full lecture transcript (~15,000
tokens) caused `gemma3:12b` to truncate the final output or produce incoherent summaries due
to context-window overflow. The model's effective useful context is approximately 4,000–6,000
tokens at quality settings.

**Chosen approach**: `smart_split()` from `core.utils.text_utils` performs boundary-aware
splitting at `map_chunk_size=4000` characters with `overlap=200` characters. Each chunk is
processed in an independent LLM call (Map pass). The Reduce pass concatenates all Map outputs
and synthesizes them into the final structured note with a YAML header and Mermaid mind-map.

**Trade-off**: 2–5× more LLM calls vs. single-pass. Accepted — correctness over speed.
For short inputs (< `chunk_threshold`), the skill uses a cheaper single-pass flow.

---

## 2026-04-20 — Content-Loss Guard (Retention Ratio Threshold)

**Decision**: After synthesis, reject the output if `len(output) / len(input) < content_loss_threshold` (default `0.01`).

**Context**: `gemma3:12b` occasionally responds with an extremely short output (e.g., "I cannot
summarize this.") when encountering ambiguous prompts or over-long contexts. A 15,000-word
lecture reduced to 3 words is a silent data-loss failure.

**Chosen approach**: The `_validate_content_retention()` method calculates the ratio. If below
threshold, raises `ValueError` and marks the calling orchestrator's task as `❌` for human review.
The threshold `0.01` is intentionally permissive — it only catches catastrophic failures, not
aggressive compression.

**Trade-off**: Legitimate ultra-short summaries (e.g., a 500-char input that compresses to 10
chars) may be incorrectly rejected. Callers can override `content_loss_threshold` in `config.yaml`.

---

## 2026-04-20 — Agentic Mermaid Retry Loop

**Decision**: Validate Mermaid diagram syntax after synthesis. If invalid, re-prompt the LLM
with the specific syntax errors and the previous broken output, up to `max_retries=3`.

**Context**: Mermaid is sensitive to whitespace and special characters. `gemma3:12b` reliably
produces structurally correct Mermaid ~85% of the time, but 15% of outputs contain subtle
errors (unclosed brackets, invalid node labels) that break rendering in Obsidian.

**Chosen approach**: After each generation, run a lightweight regex-based Mermaid validator.
On failure, construct a targeted repair prompt: `"Fix these syntax errors: {errors}\n\nPrevious output:\n{text}"`.
This agentic loop resolves >99% of Mermaid syntax issues within 2 retries.

**Trade-off**: `max_retries=3` is a hard cap. If the LLM cannot fix the Mermaid within 3
attempts, the raw broken output is returned to the caller. The caller is responsible for
fallback handling. Do NOT raise `max_retries` above 5 — it risks infinite cost escalation.

---

## 2026-04-19 — Extraction of Synthesis from `audio_transcriber` and `doc_parser`

**Decision**: Remove Phase 4 (highlight) and Phase 5 (synthesis) from `audio_transcriber`, and
Phase 3 (synthesis) from `doc_parser`. Create `note_generator` and `smart_highlighter` as
standalone, reusable synthesis skills.

**Context**: Both `audio_transcriber` and `doc_parser` contained duplicated synthesis logic
(prompts, Map-Reduce chunking, Mermaid generation). Any change to synthesis logic required
editing two separate codebases. This is a clear violation of DRY and the Single Responsibility Principle.

**Chosen approach**: `NoteGenerator` is a standalone class importable by any orchestrator.
The calling skill (e.g., `audio_transcriber/p03_merge.py`) imports it directly:
`from skills.note_generator.scripts.synthesize import NoteGenerator`. Zero duplication.

**Impact**: `audio_transcriber` reduced from 6 phases to 3. `doc_parser` reduced from 5 phases
to 4. All synthesis logic is maintained in a single location.

---

## 2026-04-30 — Async LLM Client Migration (v1.2.0)

**Decision**: Replace synchronous `generate()` calls with `async_generate()` from
`core.ai.llm_client.OllamaClient` for the Map pass in Map-Reduce flow.

**Context**: In Map-Reduce mode, each chunk can be processed independently — there is no
sequential dependency between Map calls. Running them sequentially adds unnecessary latency.

**Chosen approach**: The Map pass uses `asyncio.gather()` with an `asyncio.Semaphore(max_concurrent=2)`
to process chunks in parallel while respecting the hardware RAM constraint. The Reduce pass
remains sequential since it depends on all Map outputs.

**Trade-off**: `max_concurrent=2` limits parallelism to prevent OOM on 16GB hardware.
Increase only after RAM profiling. Adjust via `config.yaml → async.max_concurrent`.
