# DECISIONS.md — Knowledge Compiler Skill

> Technical decision log for the `knowledge-compiler` skill.

---

## 2026-04-22 — Additive-Only Wiki Update Strategy

**Decision**: `knowledge-compiler` only appends to or replaces specific sections in existing
wiki notes. It never deletes or fully overwrites existing files without an explicit `--force` flag.

**Context**: Users annotate their wiki notes directly in Obsidian (adding personal comments,
`> [AI: ...]` markers, highlighting). A full overwrite on re-compilation would silently destroy
these personal annotations, which is an unacceptable data-loss scenario.

**Chosen approach**: The compiler checks if a wiki note already exists. If it does, it updates
only the auto-generated sections (identified by `<!-- compiler-start -->` and `<!-- compiler-end -->`
HTML comment markers). User content outside these markers is preserved.

**Trade-off**: Requires managing section markers in templates. Accepted — data safety is paramount.

---

## 2026-04-22 — Glossary-Driven `[[WikiLink]]` Generation

**Decision**: Use `core.utils.glossary_manager` to detect shared terminology across notes,
then generate `[[WikiLink]]` connections between notes sharing the same key terms.

**Context**: Manual wiki linking is tedious and inconsistent. Purely LLM-based link suggestion
without a shared vocabulary produces hallucinated links to notes that don't exist.

**Chosen approach**: `glossary_manager` maintains a `priority_terms.json` shared between
`audio-transcriber` and `doc-parser`. `knowledge-compiler` scans this glossary and inserts
`[[term]]` links wherever these terms appear in compiled notes. The result is a semantically
accurate, fully navigable Obsidian knowledge graph.

**Trade-off**: Requires `priority_terms.json` to be populated (this happens in `audio-transcriber`
Phase 0 — Glossary generation). If the glossary is empty, no links will be generated.

---

## 2026-04-22 — Phase 2: Knowledge Graph Extraction (Optional)

**Decision**: Add an optional Phase 2 (`p02_extract_graph.py`) that builds a machine-readable
knowledge graph (`data/wiki/_graph/graph.json`) from the `[[WikiLink]]` connections.

**Context**: The `telegram-kb-agent` and `academic-edu-assistant` can use this graph for
enhanced multi-hop reasoning — traversing related concepts rather than flat keyword search.

**Chosen approach**: Phase 2 is independent and optional. It runs after Phase 1 and outputs
a JSON file compatible with the `core.ai.graph_store` module.

**Trade-off**: Phase 2 adds ~30 seconds of processing per subject. Disabled by default;
activated via `--extract-graph` flag.

---

## 2026-04-20 — `knowledge-compiler` Separated from `doc-parser`

**Decision**: Extract the "publish to wiki" logic from `doc-parser` Phase 5 into a standalone
`knowledge-compiler` skill.

**Context**: `doc-parser` previously had a final phase that directly wrote to `data/wiki/`.
This meant a PDF parsing failure also prevented wiki publishing, and wiki publishing logic
was embedded in an extraction-focused skill.

**Chosen approach**: `doc-parser` now outputs to `data/doc-parser/output/05_Final_Knowledge/`.
`knowledge-compiler` reads from both `doc-parser` and `audio-transcriber` outputs and handles
all wiki publishing. Clean separation of extraction vs. publication concerns.
