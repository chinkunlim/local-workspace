# Open Claw — Workspace Structure

> Last Updated: 2026-04-18
> Every file and folder in `open-claw-sandbox/` is documented here.
> Update this file whenever a file is added, removed, or significantly renamed.

---

## Root Level

```text
local-workspace/
├── docs/                 ← Single Source of Truth (SSoT) Global Docs — contains ARCHITECTURE, STRUCTURE, USER_MANUAL and all core documents
└── open-claw-sandbox/
    ├── AGENTS.md             ← Internal Agent Registry: defines the 9 core skills and RouterAgent
    ├── BOOTSTRAP.md          ← How to bring this workspace to operational state from scratch
    ├── HEARTBEAT.md          ← Known-good state snapshot; updated after each verified stable milestone
    ├── IDENTITY.md           ← Open Claw Runtime Persona: system mission, boundaries, scope of authority
    ├── SOUL.md               ← Open Claw Runtime Ethics: precision, safety, determinism
    ├── TOOLS.md              ← Local endpoints, key paths, env vars, hardware profile
    ├── USER.md               ← Operator profile: preferences, working style, constraints
    │
    ├── pyproject.toml        ← Ruff (linter/formatter) + Mypy (type checker) configuration
    ├── requirements.txt      ← All Python dependencies for core + all skills
    ├── .gitignore            ← Excludes data/, models/, logs/, __pycache__, .DS_Store
    ├── .pre-commit-config.yaml ← Pre-commit hooks: Ruff lint+format + file hygiene
    ├── .editorconfig         ← Consistent editor settings across all tools and AI agents
    │
    ├── .vscode/
    │   ├── extensions.json   ← Recommended VS Code extensions (Ruff, Mypy, Python, YAML, Markdown)
    │   └── settings.json     ← Workspace settings: format-on-save, 100-char rulers, Ruff formatter
    │
    ├── .openclaw/
    │   └── workspace-state.json  ← Open Claw agent bootstrap state (version + seed timestamp)
    │
    ├── memory/               ← AI collaboration memory layer (read by agents at every session start)
    ├── core/                 ← Shared framework — all skills import ONLY from here, never from each other
    ├── skills/               ← Self-contained skill pipelines
    ├── data/                 ← Runtime data: pipeline outputs (excluded from git)
    ├── models/               ← HuggingFace model cache (excluded from git)
    ├── logs/                 ← Service runtime logs from start.sh (excluded from git)
    ├── docs/                 ← (DEPRECATED) Old sandbox docs dir, all contents migrated to root docs/
    └── ops/                  ← Automation scripts (bootstrap.sh, check.sh) — delete one-offs after use
```

> **⚠️ Absolute Rule**: This file (`STRUCTURE.md`) is the "Global Directory Registry". Any new script, module, or directory added to this project MUST be documented here with its location and purpose. Never delete historical structure documentation; append only.

---

## `core/` — Shared Framework

All skills import from `core/`. The `core/` package must remain skill-agnostic.

```
core/
├── cli/                      ← Command-line interfaces and terminal UX
│   ├── cli.py                ← Shared argparse builder
│   ├── cli_menu.py           ← Interactive terminal menu
│   ├── cli_runner.py         ← Service layer constructing subprocess commands
│   ├── cli_config_wizard.py  ← Interactive TUI for switching model profiles
│   └── check_status.py       ← CLI helper for querying pipeline status
│
├── config/                   ← Environment and configuration management
│   ├── config_manager.py     ← YAML/JSON config loader
│   ├── config_validation.py  ← Validates config.yaml schema
│   └── inbox_config.json     ← PDF routing rules
│
├── state/                    ← State, memory, and persistence management
│   ├── state_manager.py      ← Pipeline state tracking + checklist.md
│   ├── state_backend.py      ← Backend interfaces (JSON/Redis)
│   ├── session_state.py      ← Volatile per-session state tracking
│   ├── memory_updater.py     ← Global AI memory update logic
│   └── resume_manager.py     ← Checkpoint save/load for graceful mid-run resume
│
├── orchestration/            ← Central task management and DAG routing
│   ├── router_agent.py       ← Intent parsing and skill chain resolution; subscribes to PipelineCompleted for auto-handoff
│   ├── task_queue.py         ← Single-threaded execution lock with DLQ; broadcasts PipelineCompleted event on success
│   ├── event_bus.py          ← In-process Pub/Sub event dispatcher for bridging sub-process outputs
│   ├── pipeline_base.py      ← Abstract base class for ALL Phase scripts
│   ├── run_all_pipelines.py  ← Global PID-locked pipeline orchestrator
│   └── skill_registry.py     ← Dynamic skill discovery via manifest.py
│
├── services/                 ← Background workers and security
│   ├── telegram_bot.py       ← Telegram integration for notifications and RAG queries
│   ├── inbox_daemon.py       ← Watchdog background process monitoring Inboxes; delegates routing to RouterAgent
│   ├── hitl_manager.py       ← Human-in-the-loop (HITL) interrupt management (Web UI Gates)
│   ├── human_gate.py         ← (DEPRECATED) Legacy blocking VerificationGate
│   ├── security_manager.py   ← Input security scanning (PDF sanitisation)
│   ├── sm2.py                ← SuperMemo-2 spaced repetition algorithm engine
│   └── scheduler.py          ← APScheduler background daemon for recurring tasks and Anki pushes
│
├── ai/                       ← LLM interactions and Knowledge Retrieval
│   ├── llm_client.py         ← Ollama/OpenAI client with async and circuit breaker
│   ├── hybrid_retriever.py   ← RAG retrieval engine
│   ├── graph_store.py        ← Knowledge graph interactions
│   └── knowledge_pusher.py   ← Helper to push final outputs to Obsidian/Wiki layout
│
└── utils/                    ← Stateless shared helpers
    ├── file_utils.py         ← safe_read_json, managed_tmp_dir, ensure_dir
    ├── text_utils.py         ← context-aware text chunking
    ├── path_builder.py       ← Config-driven path resolver
    ├── log_manager.py        ← Structured logger factory (rich)
    ├── atomic_writer.py      ← write-then-rename for corruption-safe file writes
    ├── error_classifier.py   ← Categorises exceptions into recoverable/fatal/user-error
    ├── bootstrap.py          ← ensure_core_path(__file__)
    ├── data_layout.py        ← Ensures all canonical data directories exist
    ├── subject_manager.py    ← Enumerates and validates subject/session directories
    ├── glossary_manager.py   ← Cross-skill terminology synchronisation
    └── diff_engine.py        ← Side-by-side HTML diff + AuditEngine
```

---

## `skills/` — Skill Pipelines

Each skill is fully self-contained. Skills share the `core/` framework but NEVER import from each other.

```
skills/
├── SKILL.md                        ← Skill registry + step-by-step guide to creating a new skill
│
├── audio_transcriber/                     ← Audio → Notion Markdown pipeline
│   ├── SKILL.md                    ← Quick-start: phases, run commands, config pointers
│   ├── config/
│   │   ├── config.yaml             ← Paths (phases section), model profiles, hardware thresholds
│   │   └── prompt.md               ← LLM system prompt templates for Phase 2–5
│   ├── docs/
│   │   ├── ARCHITECTURE.md         ← Directory layout, class hierarchy, data-flow diagram
│   │   ├── DECISIONS.md            ← Technical decision log (date-stamped entries)
│   │   └── PROJECT_RULES.md               ← AI collaboration context for this skill
│   └── scripts/
│       ├── run_all.py              ← Orchestrator: interactive 5-phase runner with resume/force
│       ├── phases/
│       │   ├── p00_glossary.py     ← Phase 0: Terminology table initialisation
│       │   ├── p01_transcribe.py   ← Phase 1: MLX-Whisper / Faster-Whisper transcription
│       │   ├── p02_proofread.py    ← Phase 2: LLM chunk-by-chunk proofreading + term guard
│       │   ├── p03_merge.py        ← Phase 3: Cross-chunk merge and refinement

│       └── utils/
│           └── subject_manager.py  ← Voice-memo-specific CLI helpers: ask_reprocess(),
│                                      should_process_task(), get_target_path()
│
└── doc_parser/                  ← PDF → Structured Markdown Knowledge Base pipeline
    ├── SKILL.md                    ← Quick-start: phases, run commands, directory guide
    ├── config/
    │   ├── config.yaml             ← Paths (phases section), model profiles, OCR/Docling thresholds
    │   ├── priority_terms.json     ← Cross-skill terminology list (shared with audio_transcriber)
    │   ├── security_policy.yaml    ← PDF security scanning rules
    │   └── selectors.yaml          ← Data source selector configuration
    ├── docs/
    │   ├── ARCHITECTURE.md         ← Subject-based hierarchy, IMMUTABLE principle, core deps
    │   ├── DECISIONS.md            ← Technical decision log
    │   └── PROJECT_RULES.md               ← AI collaboration context for this skill
    └── scripts/
        ├── run_all.py              ← QueueManager orchestrator: batch PDF queue processor
        └── phases/
            ├── p00a_diagnostic.py  ← Phase 0a: Lightweight PDF diagnostic (scan vs digital)
            ├── p01a_engine.py      ← Phase 1a: Docling deep extraction → raw_extracted.md (IMMUTABLE)
            ├── p01b_vector_charts.py ← Phase 1b: Vector chart rasterisation (pdftoppm)
            ├── p01c_ocr_gate.py    ← Phase 1c: OCR quality assessment (scan PDFs only)
            └── p01d_vlm_vision.py  ← Phase 1d: VLM visual figure description → figure_list.md

├── proofreader/                    ← Centralized proofreading and completeness verification
│   ├── SKILL.md                    ← Quick-start: modes, usage
│   ├── config/
│   │   ├── config.yaml             ← Model profiles and chunk sizes
│   │   └── prompts.yaml            ← LLM instructions for verification
│   └── scripts/
│       ├── run_all.py              ← Orchestrator
│       ├── dashboard.py            ← Asynchronous Verification Dashboard (Flask UI)
│       └── phases/
│           ├── p00_doc_proofread.py        ← Phase 0: Docling extract proofreading & image embed
│           ├── p01_transcript_proofread.py ← Phase 1: Wait logic, LLM correction, async HITL queue
│           └── p02_doc_completeness.py     ← Phase 2: PDF extract, image embedding, async HITL queue

├── smart-highlighter/              ← Standalone skill: Highlight raw markdown (Anti-Tampering)
│   ├── SKILL.md                    ← Quick-start
│   ├── config/
│   │   ├── config.yaml             ← Model profiles and chunk sizes
│   │   └── prompt.md               ← Highlighting instructions
│   ├── docs/
│   │   └── ARCHITECTURE.md         ← Standalone skill architecture
│   └── scripts/
│       └── highlight.py            ← Main entry point (SmartHighlighter class)
│
├── note-generator/                 ← Standalone skill: Synthesize structured Markdown notes
│   ├── SKILL.md                    ← Quick-start
│   ├── config/
│   │   ├── config.yaml             ← Model profiles and chunk sizes
│   │   └── prompt.md               ← Map-Reduce synthesis instructions
│   ├── docs/
│   │   └── ARCHITECTURE.md         ← Standalone skill architecture
│   └── scripts/
│       └── synthesize.py           ← Main entry point (NoteGenerator class)
│
├── academic_edu_assistant/         ← Cross-document comparison + Anki export
│   ├── SKILL.md
│   └── scripts/
│       ├── run_all.py              ← Orchestrator
│       └── phases/
│           ├── p01_compare.py      ← Phase 1: Topic comparison across documents
│           └── p02_anki.py         ← Phase 2: Anki flashcard generation
│
├── knowledge_compiler/             ← Compiles factory outputs to data/wiki/
│   ├── SKILL.md
│   └── scripts/
│       ├── run_all.py              ← Orchestrator
│       └── phases/
│           └── p01_compile.py      ← Phase 1: Compile notes into Obsidian Vault
│
├── telegram_kb_agent/              ← RAG query agent over ChromaDB index
│   ├── SKILL.md
│   └── scripts/
│       ├── bot_daemon.py           ← Telegram bot daemon (long-running)
│       ├── indexer.py              ← ChromaDB index builder
│       └── query.py                ← RAG query CLI interface
│
├── inbox_manager/                  ← CLI tool for routing rule inspection and mutation
│   ├── SKILL.md
│   └── scripts/
│       └── query.py                ← Routing rule CLI (add/remove/list rules)
│
├── academic_library_agent/ # Institution library scraper via Playwright
│   ├── manifest.py       # "academic_library_agent" declaration
│   ├── config/           # YAML profile for browser timeout/URLs
│   └── scripts/
│       ├── run_all.py    # Standard CLI entry point
│       └── phases/
│           └── p01_search_literature.py # Athens login & snapshot extract
│
├── gemini_verifier_agent/  # Multi-turn Gemini AI debate via Playwright
│   ├── manifest.py       # "gemini_verifier_agent" declaration
│   ├── config/           # YAML profile for Gemini parameters
│   └── scripts/
│       ├── run_all.py    # Standard CLI entry point
│       └── phases/
│           └── p01_ai_debate.py # AI-to-AI dialogue loop & archiving
│
├── student_researcher/     # Orchestrates academic synthesis and APA formatting
│   ├── manifest.py       # "student_researcher" declaration
│   ├── config/           # Prompts and LLM profiles
│   └── scripts/
│       ├── run_all.py    # Standard CLI entry point
│       └── phases/
│           ├── p01_claim_extraction.py # Extracts claims from raw notes
│           └── p02_synthesis.py        # Compiles debates, APA, and Obsidian tags
│
└── academic_edu_assistant/ # (Legacy) Conversational tutoring
    ├── manifest.py       # "academic_edu_assistant"
    └── scripts/          # Legacy CLI interactive loop
```

---

## `data/` — Runtime Data (excluded from git)

Created automatically on first pipeline run. Do not commit.

```
data/
├── audio_transcriber/
│   ├── input/
│   │   └── <subject>/*.m4a             ← Source audio files (drop here)
│   ├── output/
│   │   ├── 01_transcript/<subject>/    ← Phase 1 output
│   │   ├── 02_proofread/<subject>/     ← Phase 2 output
│   │   ├── 03_merged/<subject>/        ← Phase 3 output

│   ├── state/
│   │   ├── .pipeline_state.json        ← Source of truth for task progress
│   │   └── checklist.md               ← Human-readable progress table (auto-generated)
│   └── logs/
│       └── system.log                  ← Skill pipeline log
│
└── doc_parser/
    ├── input/
    │   └── <subject>/*.pdf             ← Source PDF files (drop here, by subject)
    ├── output/
    │   ├── 02_Processed/<subject>/<pdf_id>/  ← Docling extraction (IMMUTABLE)
    │   │   ├── raw_extracted.md
    │   │   ├── figure_list.md
    │   │   └── figures/
    │   ├── state/resume/<subject>/<pdf_id>/ ← Agent trace + resume state
    │   ├── 05_Final_Knowledge/<subject>/<pdf_id>/content.md ← Final knowledge
    │   ├── Error/                            ← Failed PDFs quarantined here
    │   ├── vector_db/                        ← ChromaDB vector store
    │   └── library/                          ← Aggregated knowledge library
    ├── state/
    │   ├── .pipeline_state.json
    │   └── checklist.md
    └── logs/
        └── system.log
```

---

## `memory/` — AI Collaboration Memory Layer

Read by all AI agents at the **start of every session**, in order.
Never contains runtime data — only human/agent-curated session state and architecture knowledge.

```
memory/
├── STARTUP.md       ← Canonical startup prompt + full 5-Phase session init process
├── PROJECT_RULES.md ← AI behaviour contract, hardware limits, Code Review Checklist
├── HANDOFF.md       ← Last session: completed work, system state, next starting point
├── TASKS.md         ← Prioritised task list (High / Medium / Low / Done)
├── HISTORY.md       ← Index of all archived sessions with [Archived] links
├── DECISIONS.md     ← Architectural Decision Records (ADRs)
├── ARCHITECTURE.md  ← System architecture narrative
sessions/          ← Individual session archive files (append-only)
```

**Update rules:**
| File | Update When |
|---|---|
| `STARTUP.md` | Startup sequence or session workflow changes |
| `PROJECT_RULES.md` | Project rules, hardware constraints, or checklist items change |
| `ARCHITECTURE.md` | New module, skill, or service added/removed |
| `HANDOFF.md` | End of every working session |
| `TASKS.md` | Task status changes (start / complete / add / defer) |
| `HISTORY.md` | A session is archived (auto-updated by `archive_session.py`) |
| `DECISIONS.md` | Any significant architectural decision is made |

---

---

## `identity/` — Global Identity Layer

```
identity/
└── AI_PROFILE.md           ← Global AI persona configuration and interaction style
```

---

## `docs/` — Project-Wide Documentation

```
docs/
├── ARCHITECTURE.md         ← High-level system architecture and component interactions (V9.2 Intent-Driven)
├── DEVELOPMENT_MANUAL.md   ← Chronological onboarding guide for new developers
├── CODING_GUIDELINES.md    ← Definitive engineering standards:
│                              §1  Core design principles
│                              §2  Directory structure
│                              §3  Skill development standards (phase templates, orchestrator rules)
│                              §4  Core module usage (PathBuilder, AtomicWriter, StateManager…)
│                              §5  Naming conventions (files, classes, methods, config keys)
│                              §6  Configuration schema (config.yaml required sections)
│                              §7  Error handling (severity levels, prohibited patterns)
│                              §8  CLI design (standard flags, output emoji style, interrupt behaviour)
│                              §9  Documentation standards (required docs per skill)
│                              §10 Prohibited patterns (hardcoded paths, silent exceptions…)
│                              §11 Python code style (formatting, imports, class structure)
│                              §12 Type annotations (required patterns, aliases, forbidden forms)
│                              §13 Docstrings (Google style, module/class/method templates)
│                              §14 Enforcement & tooling (Ruff, Mypy, pre-commit, review checklist)
└── OPENCLAW_TECH_STACK.md  ← Exhaustive reference of tech stack, architectural patterns, multi-agent integrations, and defensive programming mechanisms.
```

---

## `ops/` — Automation Scripts

Persistent utility scripts live here. **One-off migration scripts must be deleted after use.**

```
ops/
├── bootstrap.sh     ← First-time environment setup: installs pip deps, pre-commit hooks, verifies Ollama
└── check.sh         ← Full quality gate: Ruff lint + format + Mypy
                         Usage: ./ops/check.sh
```

**Note:** `pyproject.toml`, `.pre-commit-config.yaml`, and `requirements.txt` are at the workspace root
(not inside `ops/`) so that Ruff, Mypy, and pip work without extra flags.

---

## `models/` — Model Cache (excluded from git)

```
models/
├── models--mlx-community--whisper-large-v3-mlx/   ← MLX Whisper (audio_transcriber P1)
├── models--docling-project--docling-layout-heron/  ← Docling layout model (pdf P1b)
└── models--docling-project--docling-models/        ← Docling recognition models (pdf P1b)
```

---

## `logs/` — Service Logs (excluded from git)

Runtime logs created by `local-workspace/start.sh`.

```
logs/
├── startup.log       ← Start.sh execution log
├── openclaw.log      ← Open Claw API gateway log
├── dashboard.log     ← Flask dashboard startup log
└── open-webui.log    ← Open WebUI service log
```
