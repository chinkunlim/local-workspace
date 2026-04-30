# DECISIONS.md — Interactive Reader Skill

> Technical decision log for the `interactive_reader` skill.

---

## 2026-04-22 — `[AI-DONE:]` Idempotency Marker

**Decision**: After processing a `[AI: <instruction>]` marker, replace it with `[AI-DONE: <instruction>]` (preserving the original instruction text).

**Context**: Without idempotency protection, re-running the skill on an already-processed note
would cause the LLM to generate duplicate answers or, worse, overwrite the first answer.

**Chosen approach**: The regex scanner only matches `> [AI:` (not `> [AI-DONE:`). After
successful generation, the marker is atomically replaced with `> [AI-DONE: ...]`.
The instruction text is preserved inside `[AI-DONE:]` for traceability.

**Trade-off**: The `[AI-DONE:]` tag slightly clutters the note. Considered using a comment
tag (`<!-- AI-DONE -->`) but Obsidian renders HTML comments differently across themes.
The `[AI-DONE:]` format is the most visually consistent choice.

---

## 2026-04-22 — Context Window Strategy: Surrounding Paragraph Only

**Decision**: When constructing the LLM prompt for a marker, provide only the surrounding
~1000 characters (before and after the marker), not the entire document.

**Context**: A full document (10,000+ tokens) as context for a specific annotation instruction
causes `gemma3:12b` to produce generic summaries rather than focused answers. The model "loses"
the specific instruction when overwhelmed by a large context.

**Chosen approach**: Extract 500 characters before the marker and 500 characters after.
Use a sentence-boundary detector to ensure the extracted context doesn't break mid-sentence.

**Trade-off**: Answers may lack full document context for markers placed near the start/end
of a document. Accepted — specific, focused answers to specific questions are the priority.

---

## 2026-04-19 — Temperature = 0 (Locked)

**Decision**: All LLM calls in this skill enforce `temperature: 0`.

**Context**: Academic annotations must be reproducible. A student reviewing their notes weeks
later should see the same AI-generated content as the day it was produced.

**Chosen approach**: Temperature is hardcoded in the active config profile, not a per-invocation
parameter. The `[AI-DONE:]` marker indicates the response was generated under deterministic
settings — changing temperature would invalidate this guarantee.

---

## 2026-04-19 — Atomic In-Place File Mutation

**Decision**: Use `AtomicWriter` (write-then-rename) for all note file mutations.

**Context**: A crash, OOM, or `Ctrl+C` between `open(path, 'w')` and `file.close()` produces
a partially-written file with corrupted or empty content. For user notes, this is catastrophic.

**Chosen approach**: Write the updated content to a `.tmp` file in the same directory, then
use `os.replace()` to atomically rename it over the original. Either the full update succeeds
or the original file remains completely unchanged.
