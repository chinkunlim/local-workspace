# CHANGELOG.md — Open Claw Sandbox

All notable changes to `open-claw-sandbox/` are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [V9.1] — 2026-05-04: Performance & Robustness Hardening (Phase A)

### Added
- **Semantic Caching** (`core/ai/llm_client.py`): `SqliteSemanticCache` class caches all deterministic (`temperature=0`) LLM responses by `SHA-256(model::prompt)` key in `data/llm_cache.sqlite3`. Zero-dependency, persistent across reboots.
- **Context-Aware Model Routing** (`core/orchestration/router_agent.py`): `RouterAgent.resolve()` now assigns models based on intent complexity. High-complexity intents (`debate`, `research`, `feynman`, `analyze`, `deep`, `study`) use `deepseek-r1:14b`; others use `qwen2.5-coder:7b`. Model propagated via `OPENCLAW_ROUTER_MODEL` env var.
- **Exponential Backoff in TaskQueue** (`core/orchestration/task_queue.py`): Failed tasks now wait `5 * 2^retry_count` seconds before being re-enqueued, preventing thundering-herd retry storms. Task-specific `env` kwarg passes environment overrides to subprocesses.
- **Scheduler Queue Safety** (`core/services/scheduler.py`): APScheduler jobs (daily SM-2 push) now dispatch through the `LocalTaskQueue` via `trigger_anki_push()` instead of running synchronously, eliminating concurrent OOM risk with `inbox_daemon`.

---

## [V9.0] — 2026-05-04: Multi-Agent & GraphRAG Upgrades

### Added
- **`feynman_simulator`**: Multi-agent Socratic debate loop using Playwright to bypass login walls. Student Ollama debates Tutor Gemini.
- **GraphRAG Upgrade**: `knowledge_compiler` now extracts implicit relation triples via LLM and persists to local `networkx` (`.gpickle`).
- **Cross-Semester Linking**: `knowledge_compiler` performs ChromaDB Cosine Similarity Search to automatically inject related past notes.
- **Hybrid Retrieval**: `hybrid_retriever.py` gracefully combines 1-hop Graph expansion with dense Vector search.
- **Spaced Repetition Engine**: Pure Python SM-2 algorithm implementation in `core/services/sm2.py` coupled with `scheduler.py` (APScheduler).
- **Telegram Interactive Review**: Users receive daily pushed flashcards and can reply `/reveal <id>` and `/rate <id> <0-5>` directly in Telegram.
- **`video_ingester`**: Multimodal video ingestion pipeline using FFmpeg keyframes and MLX-Whisper word-level transcripts.

## [V8.2] — 2026-05-02: Intent-Driven RouterAgent & EventBus Handoff

### Added
- **`EventBus` Subprocess Bridging**: `TaskQueue` now emits a `PipelineCompleted` event natively when an isolated subprocess completes successfully (`returncode == 0`), solving IPC memory isolation issues.
- **Dynamic Handoff Execution**: `RouterAgent` now subscribes to `PipelineCompleted`, pops the finished skill from the resolved skill chain, determines input/output paths via `SkillRunner.resolve_synthesize_paths()`, and automatically enqueues the next skill.
- **Skill Manifests**: Every skill now exposes a `manifest.py` containing its `cli_entry`, `file_types`, and phases, enabling pure dynamic discovery by `SkillRegistry`.

### Changed
- **`inbox_daemon.py`**: Completely stripped of all hardcoded extension routing rules (e.g. `.m4a`/`.pdf`). All incoming files are now delegated to `RouterAgent` for intent parsing and dynamic skill chain resolution.
- **Documentation**: Comprehensive SSoT update across `USER_MANUAL.md`, `STRUCTURE.md`, `INDEX.md`, `DECISIONS.md`, and `HANDOFF.md` to formally deprecate the legacy static routing architecture and document the new autonomous DAG orchestration.

---

## [2.0.0] — 2026-05-02: GIGO Prevention & Verification Gate Architecture

### Added

#### `core/orchestration/human_gate.py` *(NEW)*
- Universal **Ephemeral WebUI Verification Gate** (`VerificationGate` class).
- Pure standard-library (no Flask/Gradio dependency) — `http.server` only.
- Side-by-side diff: left pane shows raw/verbatim source, right pane shows Ollama-corrected draft (editable `<textarea>`).
- HTML5 audio player with click-to-play seeking: clicking a `[? uncertain | ts ?]` token jumps to that timestamp (−2 s pre-roll).
- "Approve & Resume Pipeline" button submits the final text and shuts the server in-process; pipeline immediately continues.
- Auto port-conflict resolution (scans up to port+100).

#### `audio_transcriber` — Phase 1 (V8.2)
- `word_timestamps=True` enabled for both `mlx-whisper` and `faster-whisper`.
- **Low-Confidence Flagging**: tokens with probability < 60% are wrapped as `[? word | 12.5 ?]` (word + timestamp in seconds).
- **Light Diarization**: gaps > 1.5 s between segments produce a paragraph break (`\n\n`) for natural speaker separation.

#### `audio_transcriber` — Phase 2 Prompt (V7.3)
- **Step 1 — Disfluency Purge**: LLM instructed to remove `uh`, `um`, false starts, and mid-sentence restarts while preserving semantic content.
- **Step 2 — Low-Confidence Flag Resolution**: LLM resolves `[? word | ts ?]` tokens using PDF context and glossary; unresolvable flags are left for human review.

#### `audio_transcriber` — Phase 2 Code
- Integrated `VerificationGate` after full LLM proofreading pass.
- Raw `p1` verbatim transcript shown on left; Ollama-corrected draft on right.
- Audio file served via `/audio` endpoint for click-to-play.

#### `doc_parser` — Phase 1a (V2.0)
- **PyMuPDF 300 DPI Image Extraction**: replaces `PictureItem.get_image()` (low-res) with `fitz.Matrix(300/72)` bbox crop. Graceful fallback if PyMuPDF not installed.
- **Caption Heuristics**: scans up to 5 items below each `PictureItem` for `Fig.`/`Figure`/`圖`/`表` patterns; detected captions written to `figure_list.md`.
- **Anti-Bleed Post-processing**: strips standalone axis-label tokens (< 6 chars, purely numeric/symbol) that chart OCR bleeds into body text.
- `figure_list.md` schema extended: `原始 Caption` column added; `VLM 描述` pre-filled as `已略過 (Caption 存在)` when caption found.

#### `doc_parser` — Phase 1b-S: Text Sanitizer *(NEW)*
- **Strict Phase Isolation**: `raw_extracted.md` is IMMUTABLE. This phase writes `sanitized.md`.
- **Header/Footer Purge**: lines appearing on ≥ 40% of pages (or matching `Page N of M` pattern) are removed.
- **Hyphenation Repair**: merges end-of-line hyphens (`ex-\ntraction` → `extraction`).
- `sanitized.md` carries a provenance metadata header (lines removed, hyphenations fixed).

#### `doc_parser` — Phase 1d VLM
- **Caption Bypass**: figures with pre-existing native captions skip VLM inference entirely (saves VRAM and prevents hallucinated descriptions).

#### `knowledge_compiler` — Phase 1
- **WikiLink Dead-Link Guard**: before writing to vault, scans all `[[Link]]` occurrences and downgrades to plain text any link whose target `.md` does not exist in `wiki_dir`. Prevents Obsidian from accumulating broken link noise.

#### `academic_edu_assistant` — Phase 2 Anki
- Integrated `VerificationGate` before Anki CSV write and AnkiConnect push.
- User reviews generated Q/A cards against source comparison report; edits are persisted to CSV and pushed to Anki only after approval.

---

### Changed

- `doc_parser/run_all.py`: Phase 1b-S (Text Sanitizer) inserted between Phase 1a and Phase 1b-Vector in the pipeline sequence.
- `audio_transcriber/config/prompt.md`: Phase 2 prompt expanded with two-step Disfluency Purge + Flag Resolution instructions.

---

### Design Invariants Enforced

| Invariant                | Enforcement                                                                                                                              |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Immutable Extraction** | Phase 1 (Whisper / Docling) output is verbatim and never modified in-place. All mutations happen in subsequent, explicitly named phases. |
| **Traceable Provenance** | Each phase writes to a distinct file (`raw_extracted.md` → `sanitized.md`) so failures can be isolated to the exact phase.               |
| **Ollama-First HITL**    | `VerificationGate` only opens after Ollama has already done a first-pass correction. The human confirms rather than transcribes.         |
| **No VLM Waste**         | VLM inference is skipped when native metadata (caption) is already available.                                                            |

---

## [1.x.x] — 2026-04 (Pre-GIGO-Prevention Era)

- See `memory/ARCHITECTURE.md` → *Historical Architectural Evolution* for prior milestone descriptions.
