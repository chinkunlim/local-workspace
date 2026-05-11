# AGENTS.md — Internal Agent Registry

> **Target Audience:** Open Claw Runtime System & Developers
> **Purpose:** Serves as the central registry defining the purpose and capabilities of all specialized internal AI agents operating within the local Open Claw ecosystem.
> **Note to Development AIs:** Do not use this file for your own rules. Read `identity/AI_PROFILE.md` instead.

---

## 1. Orchestration & Routing
- **RouterAgent**: The brain of the system. Decomposes natural language intents into a DAG of skill execution pipelines. Dynamically assigns `qwen3:14b` or `qwen3:8b` based on task complexity.

## 2. Core Extraction Skills
- **audio_transcriber**: Processes `.m4a` files. Uses MLX-Whisper for raw transcription and LLMs for semantic proofreading and glossary injection.
- **doc_parser**: Processes `.pdf` files. Uses Docling to produce immutable Markdown and Vector charts.

## 3. High-Level Processing Skills
- **smart_highlighter**: Applies Markdown highlights to raw text, strictly avoiding text tampering.
- **note_generator**: Synthesizes notes using Map-Reduce chains. Permitted to use higher temperatures (`0.1`-`0.2`) for structural creativity.

## 4. Specialized Analytical Agents
- **interactive_reader**: Resolves in-place queries or annotations from human operators.
- **academic_edu_assistant**: Extracts flashcards and performs multi-document topic comparisons.
- **feynman_simulator**: Simulates Socratic debates between multiple AI personas to test logic.
- **video_ingester**: Multimodal processing pipeline for video formats.
- **knowledge_compiler**: Consolidates processed artifacts into the final Obsidian Vault (`data/wiki/`).

## 5. Interaction Agents
- **telegram_kb_agent**: Exposes a Retrieval-Augmented Generation (RAG) interface via Telegram Bot, connected to the local ChromaDB.
