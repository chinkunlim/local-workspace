# AGENTS.md — Internal Agent Registry

> **Target Audience:** Open Claw Runtime System & Developers
> **Purpose:** Central registry defining the purpose and capabilities of all specialized internal AI agents in the Open Claw 13-skill ecosystem.
> **Last Updated:** 2026-05-23 (V9.17)
> **Note to Development AIs:** Do not use this file for your own rules. Read `identity/AI_PROFILE.md` instead.

---

## 1. Orchestration & Routing

- **RouterAgent** (`core/orchestration/router_agent.py`): Decomposes natural language intents into a DAG of skill execution pipelines. Context-aware model assignment — `qwen3:14b` for high-complexity intents (`debate`, `research`, `feynman`, `analyze`); `qwen3:8b` for low-complexity routing. Reads `core/config/inbox_config.json` at init for dynamic routing table.
- **inbox_daemon** (`core/services/inbox_daemon.py`): Watchdog 24/7 filesystem listener. Implements stable-state heuristics (5-second poll, 3 consecutive size-match required) before dispatching a `TaskManifest`. Also monitors `04_final_verified/` for HITL-resume triggers.

---

## 2. Layer 2 — Extraction Skills

- **audio_transcriber**: Processes `.m4a`/`.mp3` files. MLX-Whisper word-level transcription with VAD pre-processing, low-confidence flagging (`[? word | ts ?]`), and disfluency purge.
- **doc_parser**: Processes `.pdf`, `.pptx`, `.docx`, `.xlsx` files. PyMuPDF 300 DPI extraction, multi-column anti-bleed, VLM caption bypass.
- **proofreader**: Tri-mode mutual calibration gate:
  - **Mode A** (1-to-1): Full-draft LLM grammar correction.
  - **Mode B** (1-to-many): Paragraph-level consensus voting across 3 parallel lightweight LLMs.
  - **Mode C** (many-to-1): Cross-source vocabulary calibration when slide deck + audio coexist under the same Subject.
  - Implements **Non-Blocking HITL**: serializes pending chains to `pending_chains.json`, releases VRAM, and resumes on Dashboard approval.

---

## 3. Layer 3/4 — Sequential SSoT Cognitive Chain

All four modules execute in strict order. Each independently reads `04_final_verified/` — **never consuming the previous module's LLM output** (prevents cascading contamination and OOM).

- **smart_highlighter** (Station 1): Annotates ground-truth text with `**bold**` and `==highlight==`. Anti-tampering regex anchor prevents character deletion or insertion.
- **note_generator** (Station 2): Produces structured Cornell-style outline notes with Mermaid mind maps, bilingual headers, and `#tags`.
- **feynman_simulator** (Station 3): Socratic AI-to-AI debate — local `deepseek-r1:8b` plays Student; cloud Gemini plays Tutor.
- **academic_edu_assistant** (Station 4): Extracts Q/A pairs, generates SM-2 Spaced Repetition Anki flashcards, pushes to Anki via AnkiConnect.

---

## 4. Layer 3/4 — student_researcher Multi-Ingress Funnel (Manual Trigger Only)

**Strict manual activation required.** Operates independently from the automated sequential chain.

- **student_researcher**: Multi-source academic deep-research funnel. Accepts three input streams:
  1. Chat/Q&A Markdown files from `data/raw/` (auto-staged, never auto-processed)
  2. Telegram `/idea` voice or text bypasses (auto-staged, never auto-processed)
  3. Clean `proofreader` output from `04_final_verified/` (auto-staged, never auto-processed)
  - **Phase 0**: ChromaDB semantic search → WikiLinks for related knowledge, `#incubating` + `Incubator/` for orphans.
  - **Phase 1**: Academic claim extraction using `deepseek-r1:8b` CoT reasoning.
  - **Phase 2**: `academic_library_agent` paywall traversal + `gemini_verifier_agent` AI debate.

- **academic_library_agent**: Playwright browser automation to bypass paywalled academic databases (Elsevier, Wiley, ScienceDirect, Google Scholar). Produces clean PDF/text snapshots.
- **gemini_verifier_agent**: Cloud-Local AI debate loop. `deepseek-r1:8b` (local) argues against cloud `Gemini` across 3 rounds, producing an evidence-graded Verification Report.

---

## 5. Layer 5 — Compilation

- **knowledge_compiler**: Atomic vault compiler with two key safety mechanisms:
  - **Stub Note Mode** (Dead-Link Guard): Preserves all `[[WikiLinks]]` and auto-creates minimal placeholder files in `wiki/stubs/` for unresolved targets. Eliminates red-link noise in Obsidian while maintaining full graph navigation.
  - **AtomicWriter**: `tempfile + os.replace()` for crash-safe writes — no partial files, even on power loss.
  - Extracts Entity/Relation triples to ChromaDB and networkx graph DB.

---

## 6. Interaction Agents

- **telegram_kb_agent**: RAG interface via Telegram Bot connected to local ChromaDB. Users can ask questions against their entire knowledge base via `/ask`.
- **interactive_reader**: In-place annotation resolver for Obsidian notes marked `status: rewrite`.

---

## 7. Optional / Standalone

- **inbox_manager**: CLI config mutator for `inbox_config.json` routing rules (`list`, `add`, `remove`).
- **video_ingester**: Standalone multimodal processing pipeline for video formats (FFmpeg keyframes + MLX-Whisper). Not part of the standard automated pipeline.
