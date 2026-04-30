# DECISIONS.md — Doc Parser Skill

> Technical decision log. Every non-obvious architectural choice is recorded here
> with date, context, and rationale. Future developers must read the relevant entry
> before changing anything governed by that decision.

---

## 2026-04-16 — Config-Driven Path Schema: Relative Paths + `phases:` Subtree

**Decision**: Replace the old `paths:` section (which used absolute paths with `${WORKSPACE_DIR}` interpolation) with relative paths under a standardised `paths.phases:` subtree.

**Context**: The old schema embedded absolute paths that were machine-specific and broke if the workspace was moved. The `${WORKSPACE_DIR}` interpolation was also non-standard YAML.

**Chosen approach**: All paths now relative to `data/doc_parser/`. `PathBuilder` joins them with `base_dir`. Example: `inbox: "input/01_Inbox"` resolves to `.../data/doc_parser/input/01_Inbox`.

**Impact**: Zero machine-specific content in config files. Workspace is fully portable.

---

## 2026-04-16 — StateManager Integration for doc_parser

**Decision**: Integrate `core.StateManager` with `skill_name="doc_parser"` into the `QueueManager` orchestrator, tracking all 7 phases (P0a–P3).

**Context**: doc_parser previously had no progress tracking — if a run was interrupted, there was no way to know which PDFs were partially processed.

**Chosen approach**: `startup_check()` calls `state_manager.sync_physical_files()` to populate the state from the current Inbox. Each phase completion calls `state_manager.update_task(subject, pdf_id, phase_key, "✅")`. Generated `checklist.md` is human-readable.

---

## 2026-04-15 — Docling for Phase 1a (Deep Extraction)

**Decision**: Use Docling as the primary PDF extraction engine over PyMuPDF or pdfplumber.

**Context**: Academic PDFs with complex layouts (multi-column, equations, tables, embedded figures) were mangled by simpler extractors. Docling produces semantically structured output with figure detection.

**Chosen approach**: Docling runs locally with pre-downloaded models (`models--docling-*/`). RAM capped at 2,560MB via `config.yaml`. `gc.collect()` called immediately after extraction to release memory before the next phase.

**Trade-off**: Docling is ~10× slower than PyMuPDF per page, takes 2.5GB RAM during extraction. Accepted — quality of structured output is non-negotiable for knowledge base creation.

---

## 2026-04-15 — IMMUTABLE P1a Output (`raw_extracted.md`)

**Decision**: `raw_extracted.md` is written exactly once by Docling and never overwritten by any subsequent phase.

**Context**: All downstream AI processing (VLM, synthesis) is probabilistic. If the final `content.md` is wrong or corrupted, recovery requires re-running only from P2a, not from the 10–30 minute Docling extraction (P1b).

**Chosen approach**: `AtomicWriter` writes to `raw_extracted.md`. The path is treated as immutable — if the file exists, P1a is skipped entirely. Mutations go only to `03_Synthesis/`.

---

## 2026-04-15 — Subject-Based Inbox Hierarchy

**Decision**: `01_Inbox/<subject>/` rather than a flat `01_Inbox/*.pdf` structure.

**Context**: The user manages PDFs across multiple academic subjects. A flat inbox accumulates hundreds of files with no organisational structure. Downstream output directories must mirror the subject structure.

**Chosen approach**: All Inbox scanning is subject-aware (`os.walk` + subject-folder detection). All output directories mirror `<subject>/<pdf_id>/`. `InboxDaemon` monitors at the subject-folder level.

**Trade-off**: Requires user to create subject folders before dropping PDFs. Considered acceptable — the folder structure is explicit and navigable.

---

## 2026-04-15 — Content-Loss Guard (30% Threshold)

**Decision**: P3 (`synthesis.py`) aborts write if `len(final_content) / len(raw_text) < 0.30`.

**Context**: During testing, `gemma3:12b` occasionally produced severely truncated summaries when given large context windows. A 3,000-word paper synthesised to 50 words is a silent data-loss failure.

**Chosen approach**: After synthesis, calculate `retention_ratio`. If below 0.30, log error and do NOT write `content.md`. The task state is marked `❌` for human review.

**Trade-off**: Legitimate highly-compressed academic summaries (ratio < 0.30) may be rejected. The threshold is configurable per-subject if needed.

---

## 2026-04-15 — VLM Vision in Phase 1d (Not Embedded in P3)

**Decision**: VLM figure description is a separate phase (P1d) from knowledge synthesis (P3).

**Context**: VLM calls for each figure are expensive (2–15s each depending on model). If synthesis fails and must be retried, re-running VLM is wasteful. Conversely, VLM results are the primary input to synthesis — the ordering is logical.

**Chosen approach**: P1d writes VLM results to `figure_list.md`. P3 reads `figure_list.md` alongside `raw_extracted.md`. Each phase is independently resumable.

---

## 2026-04-15 — Two-Pass OCR in Phase 1c (Gate, Not Default)

**Decision**: OCR (Tesseract) runs ONLY for PDFs identified as scan-origin in Phase 0a, NOT by default for all PDFs.

**Context**: Running Tesseract on a digital-born PDF adds 30–120 seconds per page with zero benefit — Docling handles digital text extraction perfectly. Universally applying OCR would make the pipeline impractically slow.

**Chosen approach**: Phase 0a classifies PDFs as `digital` or `scan` based on character density of the first page. Only `scan` PDFs proceed to Phase 1c. Digital PDFs skip directly to Phase 1d.

---

## [Legacy: 2026-04-13] `pdf-knowledge` v2.1 Architectural Decisions

*Note: The following decisions were made during the `pdf-knowledge` v2.1 era before the skill was refactored and renamed to `doc_parser`. They are preserved here for historical context.*

### PK-001: Execute lightweight diagnostic before deep extraction
**Decision**: Execute lightweight diagnostic before deep extraction.
**Rationale**: Catch malformed, encrypted, or low-value cases before expensive processing.
**Impact**: Lower resource waste and earlier failure transparency. (Currently implemented as Phase 00a Diagnostic).

### PK-002: Add vector chart supplementation path
**Decision**: Add vector chart supplementation path.
**Rationale**: Standard image extraction misses vector-only charts in many papers.
**Impact**: Better chart coverage and downstream analysis quality. (Largely superseded by Docling's native figure detection).

### PK-003: Add OCR confidence scoring pass
**Decision**: Add OCR confidence scoring pass.
**Rationale**: OCR uncertainty must be visible to operators and later synthesis steps.
**Impact**: Clear low-confidence page signaling and reduced silent corruption risk.
