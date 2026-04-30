# DECISIONS.md — Global Architectural Decision Records

> **Scope:** `local-workspace/` monorepo root
> **Last Updated:** 2026-04-19
> **Format:** ADR (Architectural Decision Record)

---

## [2026-04-30] P4 Sprint: Multi-Agent Architecture, Global State & HITL

**Context:** The system originally consisted of isolated scripts that passed files sequentially through the `data/` directory. There was no global state sharing, meaning user preferences (e.g., via Telegram) could not be easily passed to the `doc_parser` or `audio_transcriber`. Furthermore, any interruption required killing the process, which lacked a robust Human-in-the-Loop (HITL) recovery mechanism.

**Decision:**
1. **Global State & Memory Pool**: Implemented `MemoryPool` in `core/state/state_manager.py` using `StateBackend` for atomic JSON/Redis locking. Skills can now read/write cross-skill states from a `_global_` namespace.
2. **Intent Routing**: Introduced `core/orchestration/router_agent.py` to parse complex natural language intents using an LLM, generating a DAG (Directed Acyclic Graph) of skills to execute.
3. **HITL Pipeline Resumption**: Created `HITLPendingInterrupt` in `core/services/hitl_manager.py`. When triggered, `PipelineBase` intercepts the error, checkpoints the state to `session.json`, and gracefully exits, waiting for a `/hitl approve` signal via Telegram.
4. **Async LLM Client**: Overhauled `core/ai/llm_client.py` to use `aiohttp` and `tenacity` for exponential backoff, circuit breaking, and concurrent generation.

**Rationale:** Transitioning to a Multi-Agent orchestration framework enables the system to handle complex, chained requests autonomously while allowing safe human intervention without losing computational progress.

---

## [2026-04-19] `open-claw-sandbox/` placed at monorepo root (not inside `apps/`)

**Context:** §11.2 of CODING_GUIDELINES_FINAL recommends an `apps/` directory.

**Decision:** Keep `open-claw-sandbox/` directly at root.

**Rationale:**
- Only one application exists — `apps/` adds structure without value
- The sandbox has its own mature internal hierarchy (`core/`, `skills/`, `memory/`, `ops/`)
- `WORKSPACE_DIR` env var is already wired to the sandbox path
- Migration to `apps/open-claw-sandbox/` is straightforward if a second app is ever added

**Consequence:** The `memory/ARCHITECTURE.md` file documents this exception so AI agents understand the deviation from the standard pattern.

---

## [2026-04-20] Strict I/O Routing & Extraction Layer Purge

**Context:** The `inbox_daemon.py` was bypassing sandbox boundaries by directly writing `.pdf` files to `audio_transcriber/output/` based on `pdf_routing_rules`, causing routing leakage. Furthermore, `audio_transcriber` and `doc_parser` still contained processing prompts (highlighting, synthesis) that belong to `smart_highlighter` and `note_generator`.

**Decision:**
1. **Strict I/O Routing**: `inbox_daemon.py` now strictly routes files based on extension (`.m4a`/`.mp3` to `audio_transcriber/input/`, `.pdf` to `doc_parser/input/`). Cross-skill `output/` writes are strictly forbidden.
2. **Extraction Layer Purge**: Removed Phase 4 (highlight) and Phase 5 (synthesis) from `audio_transcriber`, and Phase 2 (highlight) and Phase 3 (synthesis) from `doc_parser`.
3. **Prompt Migration**: Integrated all highlighting rules into `smart_highlighter` and all synthesis Map-Reduce rules into `note_generator`.

**Rationale:** Enforces the single-responsibility principle. Extraction skills should only extract high-fidelity Markdown. Processing skills handle formatting and synthesis.

---

## [2026-04-19] Global `ops/check.sh` added at monorepo root

**Context:** §16.5 specifies `ops/check.sh` as the quality gate. The sandbox has its own check script, but there was no root-level script to scan the whole monorepo.

**Decision:** Add `ops/check.sh` at the monorepo root that:
1. Delegates to `open-claw-sandbox/ops/check.sh` for Python quality
2. Adds `infra/pipelines/` to the scan scope
3. Checks shell scripts via shellcheck if available

---

## [2026-04-19] `pipelines/` placed in `infra/` (not `apps/`)

**Context:** Open WebUI Pipelines is technically a runnable service.

**Decision:** Treat it as infrastructure, not an application.

**Rationale:** It is a plugin runtime for the LLM proxy layer — it has no user-facing business logic unique to this project. All other infrastructure services (LiteLLM, Open WebUI) are also in `infra/`.

---

## [2026-04-18] Monorepo §11.2 structure applied to `local-workspace/`

**Context:** Previously, `local-workspace/` had no standard monorepo structure.

**Decision:** Apply §11.2 structure:
- `infra/` for all infrastructure services
- `.github/` for CI/CD
- `tests/` for global test stubs
- Root-level standard files (CHANGELOG, CONTRIBUTING, SECURITY, .editorconfig, .env.example, pyproject.toml)

---

## [2026-04-18] `open-claw-workspace/` renamed to `open-claw-sandbox/`

**Context:** The original name `open-claw-workspace` was ambiguous — the entire monorepo (`local-workspace/`) is also a "workspace".

**Decision:** Rename to `open-claw-sandbox/` to precisely describe its function: a fully isolated, self-contained sandbox for Open Claw operations.

---

## [2026-04-17] Lifecycle scripts (start.sh, stop.sh, watchdog.sh) moved to `infra/scripts/`

**Context:** Scripts were scattered at the root of `local-workspace/`.

**Decision:** Move to `infra/scripts/` — they are infrastructure operations (starting/stopping services), not application code.

## [2026-04-20] P0: Task Queue Replaces Direct Subprocess (OOM Prevention)

### Decision
`inbox_daemon.py` abandoned the redundant HTTP POST mechanism to the WebUI API. Tasks are now written to the local Python Queue in `core/orchestration/task_queue.py` and executed synchronously by a single Worker thread.

### Consequence
Completely eliminates Ollama OOM crashes caused by simultaneous file arrivals. Guarantees sequential pipeline execution.

---

## [2026-04-20] P0: Extraction Layer Temperature Forced to Zero (Anti-Hallucination)

### Decision
All extraction layers (`audio_transcriber`, `doc_parser`) and annotation layers (`smart_highlighter`) have `temperature` forced to `0` in every LLM profile config.

### Consequence
Guarantees raw knowledge extraction and Markdown annotation never alter semantics, lose data, or produce hallucinations. High temperature is permitted ONLY in `note_generator` synthesis.

---

## [2026-04-20] P1: Open WebUI Bidirectional Integration [ABANDONED — superseded by local-first CLI architecture]

### Decision
Added `knowledge_pusher.py` to push notes into the Open WebUI knowledge base, and added Open Claw trigger tool scripts under `infra/open-webui/custom_tools/`. Added an Obsidian monitoring mechanism (`status: rewrite`) as a local reverse trigger point.

### Consequence
Forms a bidirectional closed loop: WebUI can call Open Claw, and Open Claw can proactively push results back to the WebUI knowledge base.

---

## [2026-04-19] P0: inbox_daemon triggers via HTTP → WebUI API (OOM prevention)

### Decision
[SUPERSEDED by 2026-04-20 Task Queue decision] `inbox_daemon._trigger_pipeline()` sends `POST /api/start` to the WebUI's `ExecutionManager` Job Queue first. Direct `subprocess.Popen` is a fallback-only path used when WebUI is not running (standalone mode). This ensures all Daemon-triggered pipeline runs are RAM-safe and serialised.

### Consequence
Batch arrivals of N files no longer spawn N concurrent LLM processes. The Queue dedup also prevents double-triggering the same skill.

---

## [2026-04-19] P0: _wait_and_trigger gains 300s timeout + stop_event (zombie thread prevention)

### Decision
Replaced the infinite `while True` poll loop with a bounded loop (`elapsed < 300s`) and a `threading.Event` stop signal. File-disappeared guard added. Debounce mechanism upgraded from `.cancel()` on `Thread` (dead code) to `Event.set()` on a `threading.Event`.

---

## [2026-04-19] P0: state_manager fcntl.flock on .pipeline_state.json (concurrent write guard)

### Decision
`_load_state()` acquires `LOCK_SH` and `_save_state()` acquires `LOCK_EX` via a companion `.lock` file. This prevents JSON corruption when a CLI process and a WebUI process write the state file concurrently.

---

## [2026-04-19] P1: ExecutionManager writes .rerun_state.json (Silent Failure elimination)

### Decision
`_run_job()` writes a lightweight `{task, status, timestamp}` record to `data/.rerun_state.json` at RUNNING, COMPLETED, FAILED, and CANCELLED transitions. The `/api/queue` endpoint can expose this log to the UI.

---

## [2026-04-19] P2: cli_runner uses PathBuilder for path resolution

### Decision
`resolve_highlight_paths()` and `resolve_synthesize_paths()` now use `PathBuilder.phase_dirs` with hardcoded strings as fallback. This keeps path resolution in sync with each skill's `config.yaml`.

---

## [2026-04-19] start.sh: path resolution fix (INFRA_DIR two-level ascent)

### Decision
`_LOCAL_WORKSPACE` is now derived as `$(dirname $(dirname $script_dir))` (two levels up from `infra/scripts/`). LiteLLM and Pipelines `cd` to `${INFRA_DIR}/litellm` and `${INFRA_DIR}/pipelines`. Dashboard wait extended to 60s.

---

## [2026-04-19] WebUI Integration: Re-run Pattern for smart-highlighter & note-generator

### Background
`smart-highlighter` and `note-generator` are standalone library-style skills invoked via Python import by the upstream pipeline phases. The question was whether to give them a dedicated WebUI input form or a Re-run mechanism against existing outputs.

### Options
1. Independent input form: User pastes arbitrary Markdown → triggers skill → output shown in browser
2. Re-run on existing phase output ✅ — User selects an existing `audio_transcriber`/`doc_parser` output file; system auto-discovers paths and re-triggers the skill against it

### Decision
Option 2 (Re-run). This avoids duplicating the data-entry UX, respects the existing Data Flow architecture, and requires no new data ingestion infrastructure. Auto-discovery logic is encapsulated in `core/cli_runner.SkillRunner.resolve_highlight_paths()` and `resolve_synthesize_paths()`.

### Consequence
New routes `POST /api/highlight` and `POST /api/synthesize` accept `skill + subject + file_id` and resolve all paths server-side.

---

## [2026-04-19] ExecutionManager Job Queue with Same-Skill Deduplication

### Background
The original `ExecutionManager` only supported one concurrent task. Starting a second task would return 409. No queueing existed.

### Decision
Upgrade to a sequential `queue.Queue` consumed by a background daemon thread. Tasks with the same `task_name` are rejected if already queued or running (deduplication via `_queued_names: list[str]`). One task runs at a time to preserve RAM safety on 16GB machines.

### Consequence
`POST /api/start`, `/api/highlight`, `/api/synthesize` now all enqueue through the same `ExecutionManager.enqueue_task()`. New `GET /api/queue` exposes queue state to the frontend.

---

## [2026-04-19] core/cli_runner.py as Single Source of Truth for Command Construction

### Decision
Extracted all subprocess command-list construction into `core/cli_runner.SkillRunner`. Both `app.py` routes and future CLI tools import from it. No command strings are duplicated between WebUI and CLI layers.

---

## [2026-04-18] Establish `memory/` as AI Reading Layer

### Background
Guidelines (§12.2) specify that AI collaboration files (CLAUDE.md, HANDOFF.md, TASKS.md, DECISIONS.md, ARCHITECTURE.md) should live in a `memory/` directory. Previously these did not exist at workspace level.

### Decision
Create `memory/` at workspace root with the five standard files. Agent startup sequence updated in `AGENTS.md` and `memory/CLAUDE.md` to reference these paths.

### Consequence
AI agents now have a standardised onboarding path. Root-level context files (AGENTS.md, IDENTITY.md, SOUL.md, USER.md) remain at root — they are workspace identity documents, not session memory.

---

## [2026-04-18] Move config files to workspace root

### Background
`pyproject.toml` and `.pre-commit-config.yaml` were in `ops/config/`. Tools like Ruff and pre-commit expect these at the project root.

### Options
1. Keep in `ops/config/` — requires `--config` flags on every tool invocation
2. Move to workspace root ✅ — standard convention, zero friction

### Decision
Move to workspace root. `ops/config/` directory deleted.

### Consequence
`ruff check .`, `mypy core/`, `pre-commit run` all work without extra flags.

---

## [2026-04-18] CODING_GUIDELINES.md as single source of truth

### Background
Three overlapping documents existed: `BASIC_RULES.md` (v1.0), `CODING_GUIDELINES.md` (v2.0), and `CODING_GUIDELINES.md`.

### Decision
Merge all three into `CODING_GUIDELINES.md` v3.0.0. Delete the other two. Store in both `docs/` and workspace `docs/`.

---

## [2026-04-17] MLX-Whisper over Docker for transcription

### Background
Earlier audio_transcriber used a Docker-based Whisper container. Docker adds startup latency and requires a daemon running.

### Decision
Switch to MLX-Whisper (native Apple Silicon). Zero Docker dependency, lower latency, better integration with macOS power management.

### Consequence
Removed all Docker references from audio_transcriber pipeline and docs.

---

## [2026-04-15] Shared `core/` framework over per-skill duplication

### Background
Early audio_transcriber had inline logging, path resolution, and state management. Adding doc_parser would duplicate all of this. A `SKILL_PARITY_ANALYSIS` conducted on 2026-04-15 highlighted that `voice-memo` (now `audio_transcriber`) was strong in CLI-centric pipelines and content-loss guards, while `pdf-knowledge` (now `doc_parser`) excelled in preflight diagnostics and security boundaries.

### Decision
Do not merge the workflows. Keep skills separate but extract shared primitives to `core/` with a `PipelineBase` abstract class. Each skill phase inherits from it.
**Note (Abandoned idea):** The analysis suggested an "optional voice dashboard for parity with pdf operations". This was later abandoned when the WebUI was fully deprecated in favour of the Telegram bot and Open Claw CLI.

### Consequence
Adding new skills requires only implementing the phase logic; infrastructure (logging, resume, paths) is inherited automatically. Both skills maintain their unique operational strengths while sharing governance.

---

## [2026-04-15] Strict `data/` separation from `skills/`

### Background
Pipeline outputs were previously mixed with source code.

### Decision
All runtime data (inputs, outputs, state, logs) lives exclusively in `data/<skill>/`. Source code in `skills/<skill>/scripts/`. No cross-contamination.

### Consequence
`git clean -fd` on `skills/` is safe. Data directory excluded from git.

---

## [2026-04-19] Technology Selection: Long-Polling vs WebSocket/Celery [ABANDONED — system migrated to CLI-first]

### Decision
Chose **Long-Polling** (frontend polls `/api/rerun/status` every 3 seconds) over Flask-SocketIO or Celery:

1. **Flask-SocketIO** requires `gevent`/`eventlet`, incompatible with the Flask dev server, and doubles deployment complexity
2. **Celery** requires a Redis broker, adding infrastructure dependency; the system is local-first, single-machine
3. **Long-Polling** was sufficient given the `ExecutionManager` already had a background Worker Thread; latency < 3s met the use case

### Consequence
`GET /api/rerun/status?task=XXX` reads the latest record from `.rerun_state.json`; frontend polls until status transitions from RUNNING/QUEUED to COMPLETE/ERROR.

---

## [2026-04-19] Job Queue RAM Protection: maxsize=5 [ABANDONED — superseded by LocalTaskQueue]

### Decision
`queue.Queue(maxsize=5)` — the 6th queued request returns False, and the caller converts this to an HTTP 409 response.
A single Worker Thread ensures only one LLM subprocess runs at a time.
