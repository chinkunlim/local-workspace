# DECISIONS.md — Academic & Education Assistant Skill

> Technical decision log for the `academic-edu-assistant` skill.
> Every non-obvious architectural choice is recorded here with date, context, and rationale.
> Future developers must read the relevant entry before changing anything governed by that decision.

---

## 2026-04-22 — RAG-Based Retrieval over Full-Document Concatenation

**Decision**: Use ChromaDB semantic retrieval (`core.ai.hybrid_retriever`) for Phase 1 comparison
rather than concatenating all documents into a single LLM prompt.

**Context**: Early testing with concatenated full-document prompts on `gemma3:12b` caused:
1. Context-window overflow for multi-document comparisons (>2 papers of ~8,000 tokens each)
2. Severe quality degradation — the LLM would focus only on the first document

**Chosen approach**: Build a per-subject ChromaDB index from all input Markdown files.
Phase 1 uses semantic queries to retrieve the most relevant passages across all documents,
then synthesizes only the retrieved passages into the comparison report. This approach scales
to unlimited document counts without context overflow.

**Trade-off**: Requires ChromaDB to be running and the index to be built before Phase 1 executes.
If the index is stale (new documents added but index not rebuilt), P1 results will be incomplete.
**Always rebuild the index after adding new documents to the subject input directory.**

---

## 2026-04-22 — Anki CSV Schema (Front, Back, Tags)

**Decision**: P2 outputs a CSV file with exactly three columns: `Front`, `Back`, `Tags`.

**Context**: Anki's import dialog is extremely rigid — it expects a specific delimiter (`;` by
default) and column order. Using a non-standard schema or JSON format breaks Anki import entirely.

**Chosen approach**: The P2 prompt explicitly instructs the LLM to produce structured output
that is post-processed into the `Front;Back;Tags` CSV format. The `Tags` column is pre-populated
with the subject name to enable Anki deck organization.

**Trade-off**: The rigid schema means the LLM cannot produce multi-field cards (e.g., audio).
Accepted — text Q&A flashcards are the primary use case for academic review.

---

## 2026-04-22 — Phase 0: Optional RSS Ingest

**Decision**: Add an optional Phase 0 (`p00_rss_ingest.py`) that fetches and converts RSS/web
content into Markdown files for the subject input directory.

**Context**: Some subjects (e.g., current AI research) require dynamic content from arXiv or
academic blogs rather than static local PDFs. Manually downloading and converting papers is
a friction point that discourages regular use.

**Chosen approach**: `p00_rss_ingest.py` accepts an RSS feed URL, downloads recent entries,
converts to Markdown, and saves to `input/<subject>/`. It is entirely optional — the orchestrator
can start from P1 if local files already exist.

**Trade-off**: Requires network access. Disabled by default; activated via `--rss-feed` flag.

---

## 2026-04-20 — Extraction from doc-parser's Synthesis Phase

**Decision**: The cross-document comparison functionality was originally a Phase 3 within
`doc-parser`. It was extracted into `academic-edu-assistant` as a standalone skill.

**Context**: `doc-parser` is strictly an extraction skill — it converts PDFs to structured
Markdown. Performing multi-document comparisons inside the extraction pipeline violated the
Single Responsibility Principle and made the pipeline unnecessarily complex.

**Chosen approach**: `academic-edu-assistant` is invoked separately by the user after `doc-parser`
completes. It reads from `doc-parser/output/` and `data/wiki/` as its input sources.

**Impact**: `doc-parser` reduced in scope to pure extraction. `academic-edu-assistant` has full
independence to evolve its comparison and flashcard logic without affecting extraction.
