# DECISIONS.md — Global Architectural Decision Records

> **Scope:** `local-workspace/` monorepo root
> **Last Updated:** 2026-04-19
> **Format:** ADR (Architectural Decision Record)

---

## [2026-04-30] P4 Sprint: Multi-Agent Architecture, Global State & HITL

**Context:** The system originally consisted of isolated scripts that passed files sequentially through the `data/` directory. There was no global state sharing, meaning user preferences (e.g., via Telegram) could not be easily passed to the `doc-parser` or `audio-transcriber`. Furthermore, any interruption required killing the process, which lacked a robust Human-in-the-Loop (HITL) recovery mechanism.

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

**Context:** The `inbox_daemon.py` was bypassing sandbox boundaries by directly writing `.pdf` files to `audio-transcriber/output/` based on `pdf_routing_rules`, causing routing leakage. Furthermore, `audio-transcriber` and `doc-parser` still contained processing prompts (highlighting, synthesis) that belong to `smart_highlighter` and `note_generator`.

**Decision:**
1. **Strict I/O Routing**: `inbox_daemon.py` now strictly routes files based on extension (`.m4a`/`.mp3` to `audio-transcriber/input/`, `.pdf` to `doc-parser/input/`). Cross-skill `output/` writes are strictly forbidden.
2. **Extraction Layer Purge**: Removed Phase 4 (highlight) and Phase 5 (synthesis) from `audio-transcriber`, and Phase 2 (highlight) and Phase 3 (synthesis) from `doc-parser`.
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
