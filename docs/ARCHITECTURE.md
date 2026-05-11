# ARCHITECTURE.md — Global System Architecture

> **Scope:** Entire `local-workspace/` monorepo
> **Last Updated:** 2026-05-04
> **Audience:** All AI agents and developers operating in this workspace

---

## System Overview

`local-workspace/` is a private monorepo that hosts a local AI automation ecosystem on macOS (16 GB RAM, Apple Silicon). It orchestrates several infrastructure services and one primary application sandbox.

```
local-workspace/                    ← Monorepo root (git repo)
│
├── openclaw-sandbox/              ← Primary App: Open Claw AI Automation
│   ├── core/                       ← Shared Python framework (sub-packages below)
│   │   ├── ai/                     ← LLM clients, RAG, vector DB
│   │   ├── cli/                    ← Terminal UI/UX, config wizards, arg parsing
│   │   ├── config/                 ← YAML config managers and validators
│   │   ├── orchestration/          ← RouterAgent, PipelineBase, TaskQueue, EventBus
│   │   ├── services/               ← Background daemons: inbox_daemon, telegram_bot, hitl_manager
│   │   ├── state/                  ← StateManager, ResumeManager, SessionState
│   │   └── utils/                  ← AtomicWriter, PathBuilder, log_manager, bootstrap
│   ├── skills/                     ← 9-skill AI pipeline ecosystem
│   ├── ops/                        ← Sandbox quality gate (check.sh, bootstrap.sh)
│   └── tests/                      ← Unit & integration tests (pytest)
│
├── infra/                          ← Infrastructure layer (LLM services, UI, proxy)
│   ├── litellm/                    ← LiteLLM OpenAI-compatible proxy (port 4000)
│   ├── open-webui/                 ← Open WebUI chat interface (port 3000)
│   ├── pipelines/                  ← Open WebUI Pipeline runner (port 9099)
│   └── scripts/                    ← Lifecycle scripts: start.sh, stop.sh, watchdog.sh
│
├── docs/                           ← Global documentation (SSoT)
│   ├── INDEX.md                    ← Master navigation index for AI agents and humans
│   ├── USER_MANUAL.md              ← End-user operational guide
│   ├── CODING_GUIDELINES.md  ← Engineering standards (v3.0.0)
│   └── STRUCTURE.md                ← Monorepo directory structure reference
│
├── memory/                         ← Global AI memory (this directory)
│   ├── ARCHITECTURE.md             ← This file — single source of truth
│   ├── DECISIONS.md                ← Global architectural decision log (ADR format)
│   ├── HANDOFF.md                  ← Session handoff records
│   ├── PROJECT_RULES.md                   ← AI agent collaboration context
│   └── TASKS.md                    ← Active task tracking
│
└── ops/                            ← Global quality gate scripts
    ├── check.sh                    ← Full monorepo quality gate
    └── generate_tree.py            ← Workspace tree generator utility
```

---

## Design Decisions

### Why `openclaw-sandbox/` is NOT inside `apps/`

1. It is the **only** application in this monorepo (no sibling apps).
2. It contains its own mature internal structure (`core/`, `skills/`, `ops/`, `tests/`).
3. Adding an `apps/` wrapper adds indirection with no benefit at this scale.
4. `WORKSPACE_DIR` environment variables already point directly to the sandbox.

**If a second application is added in the future**, create `apps/` and move both into it at that time.

### Why `pipelines/` is in `infra/` (not `apps/`)

Open WebUI Pipelines is infrastructure (a plugin runner for the LLM proxy), not an application with user-facing logic. It belongs with the other infrastructure services in `infra/`.

### Strict Extraction vs Processing Boundaries

Skills are strictly divided into **Extraction** and **Processing** layers:

1. **Ingestion (`inbox_daemon.py`)**: Watches `data/raw/` for stabilized files.
2. **Routing (`router_agent.py`)**: Resolves file intent to a skill chain (e.g., `audio_transcriber -> note_generator`) and moves the file to the initial skill's input directory.
3. **Execution (`task_queue.py`)**: Enqueues the first skill as an isolated subprocess. Upon success (exit code 0), emits a `PipelineCompleted` event carrying the remaining chain.
4. **Handoff (`router_agent.py`)**: Subscribes to `PipelineCompleted`, pops the finished skill from the chain, resolves the input/output paths, and enqueues the next skill automatically.
5. **GIGO Prevention**: Each phase enforces strict checkpoints, VAD/Hallucination guards, and Verification Gates (HITL).

### `core/` Sub-Package Refactoring (2026-05-01)

The `core/` directory was refactored from a flat module into domain-specific sub-packages to enforce high cohesion and single responsibility. **All imports must use the full sub-package path:**

| Old (broken) | New (correct) |
|---|---|
| `from core.atomic_writer import AtomicWriter` | `from core.utils.atomic_writer import AtomicWriter` |
| `from core.pipeline_base import PipelineBase` | `from core.orchestration.pipeline_base import PipelineBase` |
| `from core.state_manager import StateManager` | `from core.state.state_manager import StateManager` |
| `from core.llm_client import OllamaClient` | `from core.ai.llm_client import OllamaClient` |
| `from core.inbox_daemon import SystemInboxDaemon` | `from core.services.inbox_daemon import SystemInboxDaemon` |

---

## Service Map

| Service | Port | Directory | Started by |
|---|---|---|---|
| Ollama (LLM) | 11434 | system install | `infra/scripts/start.sh` |
| LiteLLM Proxy | 4000 | `infra/litellm/` | `infra/scripts/start.sh` |
| Open WebUI | 3000 | `infra/open-webui/` | `infra/scripts/start.sh` |
| Pipelines | 9099 | `infra/pipelines/` | `infra/scripts/start.sh` |
| Inbox Daemon | — | `openclaw-sandbox/core/services/inbox_daemon.py` | `infra/scripts/start.sh` |
| RAM Watchdog | — | `infra/scripts/watchdog.sh` | `infra/scripts/start.sh` |
| Scheduler | — | `openclaw-sandbox/core/services/scheduler.py` | `infra/scripts/start.sh` |

---

## AI Agent Entry Points

| Agent starting point | When to use |
|---|---|
| `memory/ARCHITECTURE.md` (this file) | Understanding the entire monorepo |
| `docs/INDEX.md` | Navigating to any skill or global doc |
| `openclaw-sandbox/AGENTS.md` | Sandbox rules and behaviour contract |
| `docs/CODING_GUIDELINES.md` | Engineering development standards |

---

## Core Framework (`core/`) Sub-Module Reference

| Sub-package | Module | Responsibility |
|---|---|---|
| `core/orchestration/` | `pipeline_base.py` | Abstract base class for all skill phases |
| `core/orchestration/` | `task_queue.py` | Single-threaded queue handling subprocess execution. Emits `PipelineCompleted` upon successful task completion. DLQ quarantine |
| `core/orchestration/` | `run_all_pipelines.py` | PID-locked global pipeline orchestrator |
| `core/orchestration/` | `router_agent.py` | Routes incoming files and manages skill chains (Intents). Subscribes to `PipelineCompleted` to trigger subsequent skills in a multi-skill pipeline via TaskQueue. |
| `core/orchestration/` | `event_bus.py` | In-process Pub/Sub for decoupling components. |
| `core/orchestration/` | `human_gate.py` | **Ephemeral WebUI Verification Gate** — pauses pipeline for human-in-the-loop review; side-by-side Ollama diff with click-to-play audio timestamps |
| `core/state/` | `state_manager.py` | Per-file per-phase state persistence (atomic JSON) |
| `core/state/` | `resume_manager.py` | Mid-run checkpoint save and restore |
| `core/state/` | `session_state.py` | Volatile per-session state |
| `core/utils/` | `atomic_writer.py` | Crash-safe file writes via `tempfile + os.replace()` |
| `core/utils/` | `path_builder.py` | Canonical data path resolution from `WORKSPACE_DIR` |
| `core/utils/` | `log_manager.py` | Structured logger factory with JSON mode |
| `core/utils/` | `bootstrap.py` | Locates `core/` and inserts into `sys.path` (idempotent) |
| `core/utils/` | `diff_engine.py` | Audit diff generation for content integrity checks |
| `core/utils/` | `error_classifier.py` | Exception classification (recoverable / fatal / user-error) |
| `core/ai/` | `llm_client.py` | Ollama/LM Studio client with exponential-backoff retry and `SqliteSemanticCache` (`data/llm_cache.sqlite3`, SHA-256 keyed, `temperature=0` only) |
| `core/ai/` | `hybrid_retriever.py` | RAG retrieval combining vector + keyword search |
| `core/ai/` | `graph_store.py` | Knowledge graph persistence and query |
| `core/config/` | `config_manager.py` | YAML config loading with environment override |
| `core/config/` | `config_validation.py` | Pydantic-based config schema validation |
| `core/cli/` | `cli.py` | Shared `argparse` factory for all skills |
| `core/cli/` | `cli_runner.py` | Subprocess command builders for all skills |
| `core/services/` | `inbox_daemon.py` | Watchdog daemon for universal inbox monitoring |
| `core/services/` | `security_manager.py` | PDF sanitisation and path-traversal prevention |
| `core/services/` | `telegram_bot.py` | Telegram bot long-polling daemon |

---

## Skill Ecosystem

The 9 production skills form a complete knowledge production pipeline:

```
Human / Telegram
    │
    ▼
data/raw/<Subject>/          ← Universal Inbox (only manual entry point)
    │
    ├──► inbox_daemon.py      ← Routes by file extension
    │         │
    │    ┌────┴─────────────────────────────┐
    │    │                                  │
    │    ▼                                  ▼
    │  audio_transcriber/input/       doc_parser/input/               video_ingester/input/
    │    │  (4-phase pipeline)          │  (8-phase pipeline)           │  (2-phase pipeline)
    │    │  P0: Glossary               │  P00a: Diagnostic             │  P1: Extract Keyframes
    │    │  P1: MLX-Whisper [VERBATIM] │  P00b: PNG OCR/VLM extract    │  P2: Transcribe & Interleave
    │    │     └─ Word timestamps      │  P01a: Docling extract (300DPI)│
    │    │  P2: Glossary Apply         │     └─ Caption heuristics      │
    │    │  P3: Sequence Merge         │  P01b-S: Text sanitizer        │
    │    └────────────┬───────────────┘  P01b: Vector charts           │
    │                 │                  P01c: OCR gate                │
    │                 ▼                  P01d: VLM vision desc         │
    │           proofreader/input/                                     │
    │            │ (2-phase pipeline)                                  │
    │            │ P1: Transcript Proofread                            │
    │            │ P2: Doc Completeness ───► smart_highlighter         │
    │            └─────────────────────────► note_generator ◄──────────┘
    │                     ▼                       │
    │               [ Academic Research Pipeline ]◄
    │                 ├─► student_researcher (Claim Extraction)
    │                 ├─► academic_library_agent (Elsevier/ScienceDirect & ArXiv Fallback)
    │                 ├─► gemini_verifier_agent (AI-to-AI Debate via Gemini Playwright)
    │                 ├─► feynman_simulator (Socratic Debate Loop)
    │                 └─► student_researcher (APA Synthesis & Obsidian Tags)
    │                     │
    │                     ▼
    │                  data/wiki/<Subject>/  ←────────────
    │                     │  (Obsidian Vault)
    │                     │
    │    ┌────────────────┤────────────────────────────┐
    │    │                │                            │
    │    ▼                ▼                            ▼
    │  knowledge-     interactive_reader/          ChromaDB
    │  compiler/      note_generator/              (indexed by
    │                 smart_highlighter/           telegram_kb_agent)
    │                                                   │
    │                                          telegram_kb_agent/
    │                                          academic_edu_assistant/
    │                                                   │
    └───────────────────────────────────────────────────┘
                            │
                    Telegram / Open WebUI
```

---

## Key Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `WORKSPACE_DIR` | Root of `openclaw-sandbox/` | auto-detected via `bootstrap.py` |
| `HF_HOME` | Hugging Face model cache | `openclaw-sandbox/models/` |
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_API_URL` | Full generate endpoint | `http://localhost:11434/api/generate` |
| `OPENCLAW_API_URL` | Open Claw intent engine | `http://127.0.0.1:18789` |
| `OPENCLAW_ROUTER_MODEL` | RouterAgent's intent decomposition model override (scope: `_llm_decompose` only) | `qwen3:8b` |
| `OPENCLAW_LOG_JSON` | Enable JSON structured logging | `0` (disabled) |

---

## Resilience Properties

| Property | Implementation |
|---|---|
| **Idempotency** | `StateManager` tracks per-file per-phase status; completed phases are skipped unless `--force` is passed |
| **Crash safety** | All file writes use `AtomicWriter` (`tempfile` + `os.replace()`); partial writes never corrupt state |
| **LLM timeout** | `OllamaClient` enforces 600 s read timeout + 3-attempt exponential-backoff retry |
| **Semantic caching** | `SqliteSemanticCache` in `llm_client.py` caches all `temperature=0` responses; SHA-256 keyed; stored at `data/llm_cache.sqlite3` |
| **Retry resilience** | `TaskQueue` uses exponential backoff (`5 * 2^retry_count` s) to prevent thundering-herd retry storms |
| **OOM prevention** | `PipelineBase.check_system_health()` monitors RSS + swap; pauses pipeline if thresholds exceeded |
| **Single-threaded execution** | `LocalTaskQueue` serialises all skill invocations; eliminates concurrent OOM risk |
| **Import isolation** | `core/utils/bootstrap.py` walks directory tree upward to locate `core/`; path inserted once (idempotent) |

---

## Historical Architectural Evolution

> The following milestones represent critical paradigm shifts implemented to harden the Open Claw ecosystem for production-grade robustness.

- **OOM Defense & RAM Guard** (2026-04): Addressed Ollama-induced OOM crashes by implementing explicit model unloading (`keep_alive=0`), governing context windows, and deploying a RAM Guard that throttles tasks when available memory drops below 15%.
- **Non-blocking Task Queue** (2026-04): Refactored to a single-threaded `LocalTaskQueue` with DLQ quarantine and 7200s timeout bounds, eliminating concurrent-execution OOM risks.
- **Audio-Transcriber Anti-Hallucination Pipeline** (2026-04): Established three-tier defense (Native API constraints, VAD pre-processing, Repetition Detection) and multi-clip majority-vote language detection.
- **Strict Sandboxed Routing & Decoupling** (2026-04): Remediated I/O data leakage in `inbox_daemon.py`; decoupled synthesis logic into `note_generator` and `smart_highlighter` standalone skills.
- **Bidirectional Knowledge Ecosystem** (2026-04): Formalised integration pipeline with Open WebUI and Obsidian for local-first knowledge extraction and retrieval.
- **WebUI to CLI Convergence** (2026-04): Achieved functional parity between WebUI and CLI; deprecated Flask web_ui in favour of pure-CLI autonomous operations.
- **SSoT Documentation Consolidation** (2026-04): Merged all fragmented docs into root `docs/` and `memory/` directories as the single source of truth.
- **`core/` Sub-Package Refactoring** (2026-05-01): Migrated `core/` from a flat module to domain sub-packages (`ai/`, `cli/`, `config/`, `orchestration/`, `services/`, `state/`, `utils/`) and fixed all import paths across the entire codebase.
- **GIGO Prevention & Verification Gate Architecture** (2026-05-02): Implemented production-grade HITL (Human-in-the-Loop) framework to eliminate Garbage-In-Garbage-Out risks:
  - `core/orchestration/human_gate.py`: Universal Ephemeral WebUI that pauses any pipeline phase for side-by-side Ollama diff review with click-to-play audio timestamps.
  - `audio_transcriber` V8.2: Word-level timestamps, low-confidence `[? token | ts ?]` flagging, light diarization (pause-based paragraph breaks), disfluency purge prompt, and VerificationGate integration at Phase 2.
  - `doc_parser` V2.0: PyMuPDF 300 DPI image extraction via bbox, native caption heuristics, axis-label anti-bleed, new immutable `raw_extracted.md` + sanitized `sanitized.md` Phase 1b-S, VLM bypass for captioned figures.
  - `knowledge_compiler`: WikiLink dead-link guard that downgrades `[[Dead Links]]` to plain text before vault write.
  - `academic_edu_assistant`: VerificationGate at Anki card generation for human approval before AnkiConnect push.
- **Open Claw v9.0 Multi-Agent & GraphRAG Upgrades** (2026-05): 
  - `feynman_simulator`: Multi-agent Socratic debate loop (Student Ollama vs Tutor Gemini via persistent Playwright).
  - `knowledge_compiler`: Extracted implicit relation triples via LLM and implemented Vector/Graph Hybrid Retrieval fallback. Added ChromaDB-powered Cross-Semester Semantic Linking.
  - `academic_edu_assistant`: Integrated SM-2 Spaced Repetition engine pushing interactive review cards via Telegram.
  - `video_ingester`: Added multimodal video ingestion pipeline (FFmpeg keyframes interleaved with MLX-Whisper word-level transcripts).
- **Academic Research Pipeline (2026-05-02)**: Introduced an autonomous AI-to-AI deep research architecture.
  - Replaced traditional MCPs with **Playwright Persistent Contexts** to seamlessly bypass Elsevier/ScienceDirect and Google Gemini login walls without API keys.
  - Integrated `academic_library_agent` for Paywall traversal and clean text snapshotting (minimizing Token limits).
  - Integrated `gemini_verifier_agent` for multi-turn local-Ollama vs cloud-Gemini AI debate and chat archival.
  - Integrated `student_researcher` as the master orchestrator to inject strict APA citations and Obsidian WikiLinks into the final compiled notes.
- **Phase A Performance Hardening (2026-05-04, V9.1)**:
  - `SqliteSemanticCache` in `core/ai/llm_client.py` — persistent SHA-256 keyed cache for all `temperature=0` LLM calls at `data/llm_cache.sqlite3`.
  - Exponential Backoff in `TaskQueue` — failed tasks wait `5 * 2^retry_count` seconds before re-enqueue.
  - Scheduler Queue Safety — APScheduler SM-2 push jobs now dispatch via `LocalTaskQueue` to prevent concurrent OOM.
  - Context-Aware Model Routing — `RouterAgent` assigns `qwen3:8b` (low-complexity) or `qwen3:14b` (high-complexity) based on intent keyword matching.
- **Quality-First Model Optimization (2026-05-04, V9.2)**:
  - All skills upgraded to highest-quality models for their task type (see `docs/MODEL_SELECTION.md`).
  - `note_generator`: active profile `qwen3_reasoning` (`qwen3:14b`); fallback `phi4_reasoning`.
  - `student_researcher`, `feynman_simulator`: `deepseek-r1:8b` for CoT analytical reasoning.
  - `knowledge_compiler`, `gemini_verifier_agent`, `academic_edu_assistant`, `academic_library_agent`, `interactive_reader`, `video_ingester`: `qwen3:14b`.
  - RouterAgent high-complexity model: `qwen3:14b`. Ollama model pool pruned from 12 to 7 models, saving 23.6 GB.
- **Asynchronous Verification Dashboard (2026-05-07, V9.4)**:
  - Deprecated the blocking `VerificationGate` (`_GatedHTTPServer`) which bottlenecked pipeline execution.
  - Introduced a persistent, non-blocking `dashboard.py` (Flask) that surfaces `data/proofreader/output/` alongside the original Ground Truth media (PDF, PNG, M4A) for highly contextual, asynchronous Human-in-the-Loop review.
