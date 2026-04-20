# DECISIONS.md — Architectural Decision Records

> **Last Updated:** 2026-04-19
> **Format:** ADR (Architectural Decision Record)

---

## [2026-04-20] P0: Task Queue 取代直接 Subprocess (防 OOM)

### Decision
`inbox_daemon.py` 放棄 HTTP POST 到 WebUI API 的冗餘機制，改為將任務寫入 `core/task_queue.py` 的本機 Python Queue。由單一 Worker 線程同步執行任務。

### Consequence
徹底消除瞬間湧入多個檔案時引發的 Ollama OOM 崩潰。保證 Pipeline 循序執行。

---

## [2026-04-20] P0: 萃取層溫度強制歸零 (防幻覺)

### Decision
所有萃取層 (`audio-transcriber`, `doc-parser`) 與純粹標記層 (`smart_highlighter`) 的 LLM profile config `temperature` 一律強制設為 `0`。

### Consequence
確保原始知識萃取與 Markdown 標記 100% 不變更語意、不丟失資料、不產生幻覺。高溫模型僅限於 `note_generator` 的推理階段。

---

## [2026-04-20] P1: Open WebUI 雙向接力

### Decision
新增 `knowledge_pusher.py` 將筆記推入 Open WebUI 知識庫，並在 `infra/open-webui/custom_tools/` 提供 Open Claw 觸發工具腳本，另加入 Obsidian 監控機制 (`status: rewrite`) 作為本機反向觸發點。

### Consequence
形成雙向閉環：WebUI 可呼叫 Open Claw，Open Claw 處理完能主動推送回 WebUI 知識庫。

---

## [2026-04-19] P0: inbox_daemon triggers via HTTP → WebUI API (OOM prevention)

### Decision
(已過時，被 2026-04-20 取代) `inbox_daemon._trigger_pipeline()` now sends `POST /api/start` to the WebUI's `ExecutionManager` Job Queue first. Direct `subprocess.Popen` is a fallback-only path used when WebUI is not running (standalone mode). This ensures all Daemon-triggered pipeline runs are RAM-safe and serialised.

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
2. Re-run on existing phase output ✅ — User selects an existing `audio-transcriber`/`doc-parser` output file; system auto-discovers paths and re-triggers the skill against it

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

## [2026-04-18] CODING_GUIDELINES_FINAL.md as single source of truth

### Background
Three overlapping documents existed: `BASIC_RULES.md` (v1.0), `CODING_GUIDELINES.md` (v2.0), and `CODING_GUIDELINES_FINAL.md`.

### Decision
Merge all three into `CODING_GUIDELINES_FINAL.md` v3.0.0. Delete the other two. Store in both `docs/` and workspace `docs/`.

---

## [2026-04-17] MLX-Whisper over Docker for transcription

### Background
Earlier audio-transcriber used a Docker-based Whisper container. Docker adds startup latency and requires a daemon running.

### Decision
Switch to MLX-Whisper (native Apple Silicon). Zero Docker dependency, lower latency, better integration with macOS power management.

### Consequence
Removed all Docker references from audio-transcriber pipeline and docs.

---

## [2026-04-15] Shared `core/` framework over per-skill duplication

### Background
Early audio-transcriber had inline logging, path resolution, and state management. Adding doc-parser would duplicate all of this.

### Decision
Extract shared logic into `core/` with `PipelineBase` abstract class. Each skill phase inherits from it.

### Consequence
Adding new skills requires only implementing the phase logic; infrastructure (logging, resume, paths) is inherited automatically.

---

## [2026-04-15] Strict `data/` separation from `skills/`

### Background
Pipeline outputs were previously mixed with source code.

### Decision
All runtime data (inputs, outputs, state, logs) lives exclusively in `data/<skill>/`. Source code in `skills/<skill>/scripts/`. No cross-contamination.

### Consequence
`git clean -fd` on `skills/` is safe. Data directory excluded from git.

---

## [2026-04-19] 技術選型：Long-Polling vs WebSocket/Celery

### Decision
選擇 **Long-Polling**（前端每 3 秒輪詢 `/api/rerun/status`）而非 Flask-SocketIO 或 Celery：

1. **Flask-SocketIO** 需要 `gevent`/`eventlet`，與 Flask 開發 server 不相容，且部署複雜度倍增
2. **Celery** 需要 Redis broker，增加基礎設施依賴，系統是 local-first 單機執行
3. **Long-Polling** 在 `ExecutionManager` 已有後台 Worker Thread 的前提下，已足夠；延遲 < 3s 符合使用場景

### Consequence
`GET /api/rerun/status?task=XXX` 讀取 `.rerun_state.json` 的最新記錄，前端在 RUNNING/QUEUED 狀態下持續輪詢，收到 COMPLETED/FAILED/CANCELLED 後停止。

---

## [2026-04-19] Job Queue RAM 防護：maxsize=5

### Decision
`queue.Queue(maxsize=5)` — 第 6 個排隊請求返回 False，呼叫方轉換為 HTTP 409。
單 Worker Thread 確保一次只有一個 LLM subprocess 在執行。
