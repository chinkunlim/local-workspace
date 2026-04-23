# ARCHITECTURE.md — System Architecture

> **Last Updated:** 2026-04-22
> **Status:** Stable / Production-Ready (V2 Antigravity Checkpoint)

---

## System Overview

```
local-workspace/
├── open-claw-sandbox/          ← AI automation sandbox (primary codebase)
│   ├── core/                   ← Shared framework (all skills depend on this)
│   │   └── inbox_config.json   ← Configurable PDF routing ruleset (42 rules, hot-reloaded)
│   ├── skills/                 ← Individual skill packages (Python-importable)
│   │   ├── __init__.py
│   │   ├── audio-transcriber/  ← 6-phase voice → wiki pipeline
│   │   ├── doc-parser/         ← 7-phase PDF → wiki pipeline
│   │   ├── note_generator/     ← Standalone Map-Reduce synthesis core
│   │   ├── smart_highlighter/  ← Standalone Anti-Tampering annotation core
│   │   ├── knowledge-compiler/ ← Compiles factory outputs to data/wiki/
│   │   ├── telegram-kb-agent/  ← RAG query agent over ChromaDB index
│   │   ├── academic-edu-assistant/ ← Cross-document comparison + Anki export
│   │   ├── interactive-reader/ ← In-place [AI:] annotation resolver
│   │   └── inbox-manager/      ← CLI tool for routing rule inspection and mutation
│   ├── memory/                 ← AI collaboration layer (HANDOFF, TASKS, DECISIONS…)
│   ├── docs/                   ← Documentation (STRUCTURE, CODING_GUIDELINES_FINAL)
│   └── data/                   ← Runtime data (gitignored; created on first run)
│       ├── raw/                ← Universal Inbox — only human-facing input point
│       ├── quarantine/         ← Dead Letter Queue (DLQ) for permanently failed files
│       └── wiki/               ← Obsidian Vault — final published knowledge base
├── infra/scripts/start.sh      ← Starts all infrastructure services
└── infra/scripts/stop.sh       ← Gracefully stops all services
```

---

## Core Framework (`core/`)

| Module | Responsibility |
|---|---|
| `pipeline_base.py` | Abstract base class inherited by all skill phases; provides `get_tasks()`, `check_system_health()`, spinner, and stop-signal handling |
| `path_builder.py` | Resolves all canonical data paths from `WORKSPACE_DIR`; single source of truth for directory layout |
| `state_manager.py` | Persists pipeline run state per file per phase (started / done / error) using atomic JSON writes with `fcntl.flock` |
| `resume_manager.py` | Saves and restores mid-run checkpoints for graceful resume after interruption |
| `session_state.py` | Volatile per-session state (current subject, active flags); written atomically |
| `log_manager.py` | Structured logger factory (`JsonFormatter` toggled via `OPENCLAW_LOG_JSON=1`) |
| `atomic_writer.py` | Crash-safe file writes via `tempfile` + `os.replace()`; mathematically guarantees no corruption |
| `file_utils.py` | DRY utility module (`safe_read_json`, `managed_tmp_dir`, `ensure_dir`) |
| `data_layout.py` | Initialises required `data/` subdirectory tree before each pipeline run |
| `security_manager.py` | PDF sanitisation, filename allow-listing, path-traversal prevention |
| `glossary_manager.py` | Cross-skill terminology sync from `priority_terms.json` |
| `text_utils.py` | `smart_split()` — context-aware chunker for LLM prompt windowing |
| `llm_client.py` | Unified Ollama / LM Studio client with exponential-backoff retry (3 attempts, 600 s timeout) |
| `subject_manager.py` | Enumerates and validates subject/session directories |
| `cli.py` | Shared `argparse` factory (`--process-all`, `--subject`, `--force`, `--log-json`, `--config`) |
| `cli_config_wizard.py` | Interactive TUI for runtime model-profile switching |
| `cli_runner.py` | Service layer — constructs subprocess command lists for all skills; imported by Open Claw dispatcher |
| `inbox_daemon.py` | Watchdog background daemon; detects Obsidian YAML `status: rewrite` triggers and new files |
| `task_queue.py` | `LocalTaskQueue`: Single-threaded execution lock, strict `timeout` guards, and Dead Letter Queue (DLQ) quarantine |
| `run_all_pipelines.py` | Global PID-locked pipeline orchestrator; prevents Telegram `/run` rapid-fire OOM crashes |
| `inbox_config.json` | Declarative routing ruleset; 42 pre-configured patterns; hot-reloaded on every file event |
| `error_classifier.py` | Classifies exceptions into recoverable / fatal / user-error categories |

> **Removed:** Legacy Flask `web_ui` components were purged during the V2 Headless migration. 
> The system is now driven strictly by `BotDaemon`, `SystemInboxDaemon`, and `LocalTaskQueue`.

---

## Inbox Routing Architecture

Files placed in `data/raw/<Subject>/` are automatically routed by `inbox_daemon.py`:

```
data/raw/<Subject>/          ← Human drop zone (only manual intervention point)
    ├── lecture.m4a          → audio-transcriber/input/<Subject>/
    ├── paper_ref.pdf        → audio-transcriber/output/00_glossary/<Subject>/  (audio_ref)
    ├── textbook_chapter.pdf → doc-parser/input/<Subject>/                      (doc_parser)
    └── units_ch1.pdf        → BOTH destinations above simultaneously            (both)
```

PDF routing mode is determined by matching the filename (without extension) against patterns
in `core/inbox_config.json`. Patterns prefixed with `_` are suffix-matched (case-insensitive);
all other patterns (CJK keywords) are substring-matched anywhere in the name.

---

## Audio-Transcriber Skill — 6-Phase Pipeline

```
Input: .m4a / .mp3 / .wav  →  Output: data/wiki/<Subject>/<lecture>.md

Phase 0: Glossary sync          (core/glossary_manager.py)
Phase 1: Transcription          (MLX-Whisper, Apple Silicon native)
Phase 2: Context-aware proofread (Ollama LLM + optional PDF reference)
Phase 3: Merge                  (consolidate transcript + proofread segments)
Phase 4: Highlight extraction   (delegated to skills/smart_highlighter/)
Phase 5: Synthesis              (delegated to skills/note_generator/ → data/wiki/)
```

---

## Doc-Parser Skill — 7-Phase Pipeline

```
Input: PDF file  →  Output: data/wiki/<Subject>/<pdf_id>/content.md

Phase 00a: Diagnostic           (security check + metadata extraction)
Phase 01a: PDF Engine           (Docling extraction → raw_extracted.md)
Phase 01b: Vector Charts        (vector diagram detection + captioning)
Phase 01c: OCR Gate             (adaptive OCR decision)
Phase 01d: VLM Vision           (figure/image analysis via vision LLM)
Phase 02:  Highlight            (delegated to skills/smart_highlighter/)
Phase 03:  Synthesis            (delegated to skills/note_generator/ → data/wiki/)
```

**Security rule:** Source PDF files are immutable — read-only; never modified in place.

---

## Service Map

| Service | Port | Notes |
|---|---|---|
| Ollama | 11434 | LLM inference server; auto-started by `start.sh` |
| LiteLLM | 4000 | OpenAI-compatible proxy for model routing |
| Open WebUI | 3000 | Chat UI; connects to LiteLLM + Pipelines |
| Pipelines | 9099 | Open WebUI pipeline runners |
| Open Claw CLI | — | Native intent engine; dispatches all skill invocations |
| Inbox Daemon | — | `core/inbox_daemon.py` (background thread) |
| Task Queue | — | `core/task_queue.py` (serialises skill runs, prevents OOM) |
| RAM Watchdog | — | `infra/scripts/watchdog.sh` |

---

## Data Flow

```
User (Telegram Bot / Obsidian Vault / CLI)
    │
    ├─► [Inbox Manager] -.-> Updates inbox_config.json
    │
    └─► data/raw/<Subject>/ OR Obsidian `status: rewrite` trigger
            │
            └─► inbox_daemon.py  (Watchdog daemon)
                    │
                    └─► task_queue.py (LocalTaskQueue with DLQ & 7200s timeout bounds)
                                 │
                                 ├─► doc-parser / audio-transcriber (Extraction, Immutable)
                                 │      (outputs to 03_synthesis / 03_merged)
                                 │
                                 └─► note-generator / smart-highlighter (Synthesis)
                                              │
                                              └─► data/wiki/ (Obsidian Vault)
                                                        │
                                                        ├─► Open WebUI Knowledge API
                                                        │
                                     ┌───────────┴───────────┐
                                     │                       │
                                 Obsidian               ChromaDB index
                                 (human review)         (RAG queries via
                                                     telegram-kb-agent /
                                                    academic-edu-assistant)
```

---

## Key Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `WORKSPACE_DIR` | Root of `open-claw-sandbox/` | auto-detected via `bootstrap.py` |
| `HF_HOME` | Hugging Face model cache | `open-claw-sandbox/models/` |
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_API_URL` | Full generate endpoint | `http://localhost:11434/api/generate` |
| `OPENCLAW_API_URL` | Open Claw intent engine | `http://127.0.0.1:18789` |

---

## Resilience Properties

| Property | Implementation |
|---|---|
| **Idempotency** | `StateManager` tracks per-file per-phase status; completed phases are skipped unless `--force` is passed |
| **Crash safety** | All file writes use `AtomicWriter` (`tempfile` + `os.replace()`); partial writes never corrupt state |
| **LLM timeout** | `OllamaClient` enforces 600 s read timeout + 3-attempt exponential-backoff retry |
| **OOM prevention** | `PipelineBase.check_system_health()` monitors RSS + swap; pauses pipeline if thresholds exceeded |
| **Import isolation** | `core/bootstrap.py` walks the directory tree upward to locate `core/`; path is inserted once (idempotent) |
