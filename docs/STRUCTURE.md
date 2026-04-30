# Open Claw — Workspace Structure

> Last Updated: 2026-04-18
> Every file and folder in `open-claw-sandbox/` is documented here.
> Update this file whenever a file is added, removed, or significantly renamed.

---

## Root Level

```text
local-workspace/
├── docs/                 ← Single Source of Truth (SSoT) 全域文件目錄 — 包含 ARCHITECTURE, STRUCTURE, USER_MANUAL 等所有核心文檔
└── open-claw-sandbox/
    ├── AGENTS.md             ← Non-negotiable rules and startup context for AI agents
    ├── BOOTSTRAP.md          ← How to bring this workspace to operational state from scratch
    ├── HEARTBEAT.md          ← Known-good state snapshot; updated after each verified stable milestone
    ├── IDENTITY.md           ← Open Claw system identity: mission, boundaries, personality
    ├── SOUL.md               ← Quality and discipline principles (the "why" behind the rules)
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
    ├── docs/                 ← (DEPRECATED) 舊沙盒文件目錄，所有內容均已遷移至 root docs/
    └── ops/                  ← Automation scripts (bootstrap.sh, check.sh) — delete one-offs after use
```

> **⚠️ 絕對原則**：本檔案 (`STRUCTURE.md`) 乃是「全域腳本唯一註冊表」。任何在此專案新增的腳本、模組或目錄，都必須在此詳述功能與位置。嚴禁刪除任何歷史說明與結構，只能新增或補充。

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
│   ├── router_agent.py       ← LLM-based DAG parser for intent routing
│   ├── task_queue.py         ← LocalTaskQueue: Single-threaded execution lock with DLQ
│   ├── scheduler.py          ← Task scheduling mechanisms
│   ├── event_bus.py          ← Pub/Sub event dispatcher
│   ├── pipeline_base.py      ← Abstract base class for ALL Phase scripts
│   ├── run_all_pipelines.py  ← Global PID-locked pipeline orchestrator
│   └── skill_registry.py     ← Dynamic skill discovery and registry
│
├── services/                 ← Background workers and security
│   ├── telegram_bot.py       ← Telegram integration for notifications and RAG queries
│   ├── inbox_daemon.py       ← Watchdog background process monitoring Inboxes
│   ├── hitl_manager.py       ← Human-in-the-loop (HITL) interrupt management
│   └── security_manager.py   ← Input security scanning (PDF sanitisation)
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
├── audio-transcriber/                     ← Audio → Notion Markdown pipeline
│   ├── SKILL.md                    ← Quick-start: phases, run commands, config pointers
│   ├── config/
│   │   ├── config.yaml             ← Paths (phases section), model profiles, hardware thresholds
│   │   └── prompt.md               ← LLM system prompt templates for Phase 2–5
│   ├── docs/
│   │   ├── ARCHITECTURE.md         ← Directory layout, class hierarchy, data-flow diagram
│   │   ├── DECISIONS.md            ← Technical decision log (date-stamped entries)
│   │   └── CLAUDE.md               ← AI collaboration context for this skill
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
└── doc-parser/                  ← PDF → Structured Markdown Knowledge Base pipeline
    ├── SKILL.md                    ← Quick-start: phases, run commands, directory guide
    ├── config/
    │   ├── config.yaml             ← Paths (phases section), model profiles, OCR/Docling thresholds
    │   ├── priority_terms.json     ← Cross-skill terminology list (shared with audio-transcriber)
    │   ├── security_policy.yaml    ← PDF security scanning rules
    │   └── selectors.yaml          ← Data source selector configuration
    ├── docs/
    │   ├── ARCHITECTURE.md         ← Subject-based hierarchy, IMMUTABLE principle, core deps
    │   ├── DECISIONS.md            ← Technical decision log
    │   └── CLAUDE.md               ← AI collaboration context for this skill
    └── scripts/
        ├── run_all.py              ← QueueManager orchestrator: batch PDF queue processor
        └── phases/
            ├── p00a_diagnostic.py  ← Phase 0a: Lightweight PDF diagnostic (scan vs digital)
            ├── p01a_engine.py      ← Phase 1a: Docling deep extraction → raw_extracted.md (IMMUTABLE)
            ├── p01b_vector_charts.py ← Phase 1b: Vector chart rasterisation (pdftoppm)
            ├── p01c_ocr_gate.py    ← Phase 1c: OCR quality assessment (scan PDFs only)
            └── p01d_vlm_vision.py  ← Phase 1d: VLM visual figure description → figure_list.md

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
├── academic-edu-assistant/         ← Cross-document comparison + Anki export
│   ├── SKILL.md
│   └── scripts/
│       ├── run_all.py              ← Orchestrator
│       └── phases/
│           ├── p01_compare.py      ← Phase 1: Topic comparison across documents
│           └── p02_anki.py         ← Phase 2: Anki flashcard generation
│
├── knowledge-compiler/             ← Compiles factory outputs to data/wiki/
│   ├── SKILL.md
│   └── scripts/
│       ├── run_all.py              ← Orchestrator
│       └── phases/
│           └── p01_compile.py      ← Phase 1: Compile notes into Obsidian Vault
│
├── telegram-kb-agent/              ← RAG query agent over ChromaDB index
│   ├── SKILL.md
│   └── scripts/
│       ├── bot_daemon.py           ← Telegram bot daemon (long-running)
│       ├── indexer.py              ← ChromaDB index builder
│       └── query.py                ← RAG query CLI interface
│
├── inbox-manager/                  ← CLI tool for routing rule inspection and mutation
│   ├── SKILL.md
│   └── scripts/
│       └── query.py                ← Routing rule CLI (add/remove/list rules)
│
└── interactive-reader/             ← In-place [AI:] annotation resolver
    ├── SKILL.md
    └── scripts/
        ├── run_all.py              ← Orchestrator
        └── phases/
            └── p01_interactive.py  ← Phase 1: Resolve in-file AI annotations
```

---

## `data/` — Runtime Data (excluded from git)

Created automatically on first pipeline run. Do not commit.

```
data/
├── audio-transcriber/
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
└── doc-parser/
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
├── CLAUDE.md        ← Project rules, AI behaviour contract, mandatory startup sequence, hardware constraints
├── ARCHITECTURE.md  ← System full picture: core modules, skill pipelines, service map, data flow
├── HANDOFF.md       ← Last session: what was completed, current system state, next starting point
├── TASKS.md         ← Prioritised task list (High / Medium / Low / Done)
└── DECISIONS.md     ← Architectural Decision Records (ADRs) — why we made each key design choice
```

**Update rules:**
| File | Update When |
|---|---|
| `CLAUDE.md` | Project rules or hardware constraints change |
| `ARCHITECTURE.md` | New module, skill, or service added/removed |
| `HANDOFF.md` | End of every working session |
| `TASKS.md` | Task status changes (start / complete / add / defer) |
| `DECISIONS.md` | Any significant architectural decision is made |

---

## `docs/` — Project-Wide Documentation

```
docs/
└── CODING_GUIDELINES.md    ← Definitive engineering standards:
                               §1  Core design principles
                               §2  Directory structure
                               §3  Skill development standards (phase templates, orchestrator rules)
                               §4  Core module usage (PathBuilder, AtomicWriter, StateManager…)
                               §5  Naming conventions (files, classes, methods, config keys)
                               §6  Configuration schema (config.yaml required sections)
                               §7  Error handling (severity levels, prohibited patterns)
                               §8  CLI design (standard flags, output emoji style, interrupt behaviour)
                               §9  Documentation standards (required docs per skill)
                               §10 Prohibited patterns (hardcoded paths, silent exceptions…)
                               §11 Python code style (formatting, imports, class structure)
                               §12 Type annotations (required patterns, aliases, forbidden forms)
                               §13 Docstrings (Google style, module/class/method templates)
                               §14 Enforcement & tooling (Ruff, Mypy, pre-commit, review checklist)
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
├── models--mlx-community--whisper-large-v3-mlx/   ← MLX Whisper (audio-transcriber P1)
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
