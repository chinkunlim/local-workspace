# Open Claw — Workspace Structure

> Last Updated: 2026-04-18
> Every file and folder in `open-claw-workspace/` is documented here.
> Update this file whenever a file is added, removed, or significantly renamed.

---

## Root Level

```
open-claw-workspace/
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
├── docs/                 ← Project-wide documentation (STRUCTURE, CODING_GUIDELINES_FINAL)
└── ops/                  ← Automation scripts (bootstrap.sh, check.sh) — delete one-offs after use
```

---

## `core/` — Shared Framework

All skills import from `core/`. The `core/` package must remain skill-agnostic.

```
core/
├── __init__.py               ← Public API: imports all exported symbols for "from core import X"
│
├── bootstrap.py              ← ensure_core_path(__file__): one-liner sys.path fix
│                                Replaces the old 10-line "Boundary-Safe Init" boilerplate.
│
├── pipeline_base.py          ← Abstract base class for ALL Phase scripts and Orchestrators.
│                                Provides: self.dirs, self.llm, self.state_manager,
│                                self.info/warning/error logging, interrupt handling.
│
├── path_builder.py           ← Config-driven path resolver. Reads paths.phases from
│                                config.yaml; no hardcoded if-skill_name branches.
│                                Properties: canonical_dirs, phase_dirs, log_file, state_file.
│
├── state_manager.py          ← Pipeline state tracking + checklist.md rendering.
│                                Manages .pipeline_state.json per skill.
│                                Supports skill-specific phase sets (voice: p1-p5, pdf: p1a-p2b).
│
├── config_manager.py         ← YAML/JSON config loader with get_nested() and get_section().
│
├── config_validation.py      ← Validates config.yaml schema at pipeline startup.
│
├── llm_client.py             ← OllamaClient: generate(), unload_model(), retry logic, timeouts.
│
├── atomic_writer.py          ← AtomicWriter: write-then-rename for corruption-safe file writes.
│
├── diff_engine.py            ← DiffEngine (side-by-side HTML diff) + AuditEngine (changelog
│                                aggregation). Skill-agnostic — any two text files.
│
├── glossary_manager.py       ← Cross-skill terminology synchronisation.
│                                Reads/writes priority_terms.json shared between skills.
│
├── text_utils.py             ← smart_split(): context-aware text chunking for LLM prompts.
│
├── security_manager.py       ← Input security scanning (PDF sanitisation; path traversal guard).
│
├── resume_manager.py         ← Checkpoint save/load for graceful mid-run resume.
│
├── error_classifier.py       ← Categorises exceptions into recoverable / fatal / user-error.
│
├── log_manager.py            ← Structured logger factory (file + console, emoji prefixes).
│
├── data_layout.py            ← Ensures all canonical data directories exist before pipeline runs.
│
├── cli.py                    ← Shared argparse builder: adds --subject, --force, --resume,
│                                --interactive flags to any skill's CLI.
│
├── cli_config_wizard.py      ← Interactive TUI for switching model profiles in config.yaml.
│                                Run: python3 core/cli_config_wizard.py --skill <skill-name>
│
├── inbox_daemon.py           ← SystemInboxDaemon: watchdog background process that monitors
│                                all skill Inboxes and triggers pipelines on new files.
│                                Started/stopped by local-workspace/start.sh and stop.sh.
│
└── web_ui/
    ├── app.py                ← Flask API server for the Central Dashboard (port 5001).
    │                            Routes: /, /api/status, /api/logs, /api/start, /api/stop,
    │                            /api/diff/phases, /api/diff/subjects, /api/diff/files, /api/diff
    ├── execution_manager.py  ← Manages subprocess lifecycle: spawn, stdout streaming,
    │                            SIGTERM/SIGKILL terminate, log buffer with cursor pagination.
    └── templates/
        └── index.html        ← Single-page dashboard: status panels, live log viewer,
                                 Review Board with GitHub-style line-by-line diff rendering.
```

---

## `skills/` — Skill Pipelines

Each skill is fully self-contained. Skills share the `core/` framework but NEVER import from each other.

```
skills/
├── SKILL.md                        ← Skill registry + step-by-step guide to creating a new skill
│
├── voice-memo/                     ← Audio → Notion Markdown pipeline
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
│       │   ├── p04_highlight.py    ← Phase 4: Key-concept highlighting
│       │   └── p05_synthesis.py    ← Phase 5: Notion-ready knowledge synthesis
│       └── utils/
│           └── subject_manager.py  ← Voice-memo-specific CLI helpers: ask_reprocess(),
│                                      should_process_task(), get_target_path()
│
└── pdf-knowledge/                  ← PDF → Structured Markdown Knowledge Base pipeline
    ├── SKILL.md                    ← Quick-start: phases, run commands, directory guide
    ├── config/
    │   ├── config.yaml             ← Paths (phases section), model profiles, OCR/Docling thresholds
    │   ├── priority_terms.json     ← Cross-skill terminology list (shared with voice-memo)
    │   ├── security_policy.yaml    ← PDF security scanning rules
    │   └── selectors.yaml          ← Data source selector configuration
    ├── docs/
    │   ├── ARCHITECTURE.md         ← Subject-based hierarchy, IMMUTABLE principle, core deps
    │   ├── DECISIONS.md            ← Technical decision log
    │   └── CLAUDE.md               ← AI collaboration context for this skill
    └── scripts/
        ├── run_all.py              ← QueueManager orchestrator: batch PDF queue processor
        └── phases/
            ├── p01a_diagnostic.py  ← Phase 1a: Lightweight PDF diagnostic (scan vs digital)
            ├── p01b_engine.py      ← Phase 1b: Docling deep extraction → raw_extracted.md (IMMUTABLE)
            ├── p01c_vector_charts.py ← Phase 1c: Vector chart rasterisation (pdftoppm)
            ├── p01d_ocr_gate.py    ← Phase 1d: OCR quality assessment (scan PDFs only)
            ├── p02a_vlm_vision.py  ← Phase 2a: VLM visual figure description → figure_list.md
            └── p02b_synthesis.py   ← Phase 2b: Map-Reduce synthesis → content.md
```

---

## `data/` — Runtime Data (excluded from git)

Created automatically on first pipeline run. Do not commit.

```
data/
├── voice-memo/
│   ├── input/
│   │   └── <subject>/*.m4a             ← Source audio files (drop here)
│   ├── output/
│   │   ├── 01_transcript/<subject>/    ← Phase 1 output
│   │   ├── 02_proofread/<subject>/     ← Phase 2 output
│   │   ├── 03_merged/<subject>/        ← Phase 3 output
│   │   ├── 04_highlighted/<subject>/   ← Phase 4 output
│   │   └── 05_notion_synthesis/<subject>/ ← Phase 5 final output
│   ├── state/
│   │   ├── .pipeline_state.json        ← Source of truth for task progress
│   │   └── checklist.md               ← Human-readable progress table (auto-generated)
│   └── logs/
│       └── system.log                  ← Skill pipeline log
│
└── pdf-knowledge/
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
├── models--mlx-community--whisper-large-v3-mlx/   ← MLX Whisper (voice-memo P1)
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
