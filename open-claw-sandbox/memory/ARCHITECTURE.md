# ARCHITECTURE.md — System Architecture

> **Last Updated:** 2026-04-18
> **Status:** Production-stable

---

## System Overview

```
local-workspace/
├── open-claw-sandbox/      ← AI automation sandbox (this repo)
│   ├── core/                 ← Shared framework (all skills depend on this)
│   ├── skills/               ← Individual skill modules
│   │   ├── audio-transcriber/       ← 6-phase audio → Notion pipeline
│   │   ├── doc-parser/    ← 7-phase PDF → knowledge base pipeline
│   │   ├── smart-highlighter/← Standalone Anti-Tampering annotation core
│   │   └── note-generator/   ← Standalone Map-Reduce synthesis core
│   ├── memory/               ← AI collaboration memory (CLAUDE, HANDOFF, TASKS...)
│   ├── docs/                 ← Workspace documentation (STRUCTURE, GUIDELINES)
│   └── ops/                  ← Automation scripts and tooling config
├── watchdog.sh               ← RAM guardian daemon (speculative pages monitor)
├── start.sh                  ← Starts 7 core services
└── stop.sh                   ← Gracefully stops all services
```

---

## Core Framework (`core/`)

| Module | Responsibility |
|---|---|
| `pipeline_base.py` | Abstract base class all skill phases inherit from |
| `path_builder.py` | Resolves all canonical data paths from WORKSPACE_DIR |
| `state_manager.py` | Manages pipeline run state (started/running/done/error) |
| `resume_manager.py` | Checkpoint save/load for graceful mid-run resume |
| `session_state.py` | Per-session volatile state (current subject, flags) |
| `log_manager.py` | Structured logger factory (file + console, emoji prefixes) |
| `data_layout.py` | Creates all required data directories before pipeline runs |
| `security_manager.py` | PDF sanitisation, path traversal guard |
| `glossary_manager.py` | Cross-skill terminology sync (priority_terms.json) |
| `text_utils.py` | smart_split() — context-aware LLM prompt chunking |
| `llm_client.py` | Unified Ollama API client |
| `subject_manager.py` | Lists and validates subject/session directories |
| `cli.py` | Shared argparse builder (--subject, --force, --resume) |
| `cli_config_wizard.py` | Interactive TUI for model profile switching |
| `inbox_daemon.py` | Watchdog that monitors Inbox dirs and triggers pipelines |
| `error_classifier.py` | Classifies exceptions: recoverable / fatal / user-error |
| `web_ui/app.py` | Flask API server — Central Dashboard (port 5001) |

---

## Audio-Transcriber Skill — 6-Phase Pipeline

```
Input: .m4a / .mp3 / .wav file  →  Output: Notion-ready markdown

Phase 0: Glossary sync         (core/glossary_manager.py)
Phase 1: Transcription         (MLX-Whisper, native macOS)
Phase 2: Proofreading          (Ollama LLM — Qwen3:14B)
Phase 3: Merge                 (consolidate transcript + proofread)
Phase 4: Highlight extraction  (key terms, action items)
Phase 5: Synthesis             (Notion-structured summary)
```

**Data paths:** `data/audio-transcriber/<subject>/` with subdirs: `input/`, `01_transcribed/`, `02_proofread/`, `03_merged/`, `04_highlighted/`, `05_synthesized/`, `logs/`, `state/`

---

## Doc-Parser Skill — 7-Phase Pipeline

```
Input: PDF file  →  Output: structured knowledge base entry

Phase 00a: Diagnostic          (pre-flight security + metadata check)
Phase 01a: PDF Engine          (Docling extraction)
Phase 01b: Vector Charts       (vector diagram detection)
Phase 01c: OCR Gate            (decides if OCR is needed)
Phase 01d: VLM Vision          (figure/image analysis via VLM)
Phase 02:  Highlight           (anti-tampering annotation)
Phase 03:  Synthesis           (Map-Reduce → structured knowledge)
```

**Data paths:** `data/doc-parser/<subject>/` with subdirs: `inbox/`, `processed/`, `error/`, `state/`, `logs/`

**Security rule:** Original PDF files are IMMUTABLE — never modified, only read.

---

## Service Map (started by `start.sh`)

| Service | Port | Process |
|---|---|---|
| Ollama | 11434 | LLM inference server |
| LiteLLM | 4000 | OpenAI-compatible proxy |
| Open WebUI | 3000 | Chat interface |
| Pipelines | 9099 | Open WebUI pipeline runners |
| Open Claw Dashboard | 5001 | `core/web_ui/app.py` |
| Inbox Daemon | — | `core/inbox_daemon.py` (background) |
| Watchdog | — | `watchdog.sh` (RAM guardian) |

---

## Data Flow

```
User drops file → Inbox Daemon detects → triggers run_all.py → phases execute in sequence
                                                              → state saved per phase
                                                              → logs written to data/<skill>/logs/
                                                              → Dashboard shows live status
```

---

## Key Environment Variables

| Variable | Purpose |
|---|---|
| `WORKSPACE_DIR` | Root of open-claw-sandbox/ |
| `HF_HOME` | Points to models/ (Hugging Face cache) |
| `OLLAMA_HOST` | Ollama server URL (default: http://localhost:11434) |
