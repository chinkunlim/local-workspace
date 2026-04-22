# AI Master Guide: Open Claw Ecosystem

> **Version**: 2.0.0 "Antigravity" Checkpoint  
> **Target Audience**: AI Agents, System Architects, and DevOps Engineers  
> **Objective**: Define the foundational operating principles, architecture invariants, and safety mechanisms of the Open Claw Personal Knowledge Management System (PKMS).

---

## 1. Architectural Paradigm: Headless Dual-Engine Orchestration

The Open Claw ecosystem has evolved from a monolithic Flask-bound application to a robust, headless asynchronous architecture designed for 24/7 continuous operation.

### 1.1 The Orchestration Layer
- **`SystemInboxDaemon`**: A highly resilient, watchdog-driven background process. It monitors multiple `/input/` drop-zones utilizing atomic debouncing and strict lockfiles (`run_pipelines.lock`) to prevent race conditions during rapid I/O events.
- **`BotDaemon`**: A Telegram-based command-and-control interface. It facilitates asynchronous dispatching (`/run`, `/pause`) and status telemetry (`/status`), entirely decoupling the user interface from the heavy processing logic.

### 1.2 Pipeline Decoupling
Open Claw enforces a strict separation of concerns between Extraction and Synthesis:
- **Extraction Skills** (`audio-transcriber`, `doc-parser`): Responsible solely for converting raw unstructured data (.m4a, .pdf) into structured, **immutable** Markdown intermediate representations.
- **Synthesis Skills** (`note-generator`, `smart-highlighter`): Operate on the immutable outputs to generate context-aware knowledge artifacts (e.g., Literature Matrices, Anki cards).

---

## 2. DRY Core Modularization Standards

Redundancy is heavily penalized. All shared utilities must reside in the `core/` package. Skills are strictly prohibited from implementing duplicate utility functions or cross-importing from other skills.

### 2.1 The Standardized CLI (`core/cli.py`)
All skill entry points must utilize the `build_skill_parser()` factory. This enforces a universal CLI contract across the ecosystem:
- `--process-all`: Engages headless batch-processing mode.
- `--force`: Bypasses idempotency checks.
- `--subject`: Scopes execution to a specific taxonomy node.
- `--config`: Allows runtime configuration injection.
- `--log-json`: Toggles structured JSON telemetry for headless aggregation.

### 2.2 Defensive I/O (`core/file_utils.py` & `core/atomic_writer.py`)
- **Atomic Writes**: `AtomicWriter.write_text()` and `write_json()` must be used for all state mutations. They utilize a write-to-temp-then-rename strategy, mathematically guaranteeing that a mid-write SIGKILL cannot corrupt the Obsidian vault or system state.
- **Safe Parsing**: `safe_read_json()` handles all state deserialization, silencing `JSONDecodeError`s and preventing pipeline crashes on corrupted inputs.
- **Managed Lifecycle**: `managed_tmp_dir()` context managers ensure deterministic cleanup of ephemeral data (e.g., VAD wav chunks) even during fatal exceptions.

---

## 3. RAM Safety Guard & OOM Defense

Given the severe VRAM/RAM constraints of running local LLMs (Ollama) alongside heavy extraction engines (Docling, Whisper), Open Claw implements a multi-tiered defense against Out-Of-Memory (OOM) failures.

### 3.1 The Dead Letter Queue (DLQ) Architecture
The `LocalTaskQueue` acts as the primary orchestrator for pipeline execution:
- **Single-Threaded Execution**: Forces strictly sequential processing of heavy tasks, preventing concurrent model loads.
- **Timeout Bounds**: Every pipeline execution is wrapped in a hard `subprocess.TimeoutExpired` bound (default: 7200s) to prevent silent deadlocks from headless browsers (Playwright) or stalling VLMs.
- **Poison Pill Quarantine**: If a task exceeds `max_retries=3`, the offending file is intercepted and relocated to `data/quarantine/{skill}/`, and an exception stack is logged in `quarantine_log.json`. This definitively solves infinite OOM crash loops.

### 3.2 Explicit Model Lifecycle Management
- **Zero-Accumulation VRAM**: Every Phase that initializes an Ollama model must wrap the execution in a `try...finally` block that explicitly calls `self.llm.unload_model()`.
- **Garbage Collection**: Orchestrators manually invoke `gc.collect()`, `mx.clear_cache()`, and `torch.cuda.empty_cache()` between major phase transitions.

### 3.3 Prompt Purity & Hallucination Prevention
- **Strict Temperature Control**: Data extraction and reasoning tasks (e.g., `knowledge-compiler`, `interactive-reader`) are hardcoded to `temperature: 0` in their respective `config.yaml` to enforce deterministic outputs and eliminate hallucination drift.

---

## 4. Observability & Telemetry

### 4.1 Structured Logging (`core/log_manager.py`)
Open Claw supports dual-mode logging:
- **Interactive Mode**: Emits human-readable logs with semantic emoji prefixes.
- **Headless Mode**: Triggered via `OPENCLAW_LOG_JSON=1`, the `JsonFormatter` emits structured JSON lines containing precise timestamps, caller context, and `exc_info` tracebacks, primed for external ingestion (e.g., ELK, Datadog).

### 4.2 State Invariants (`core/state_manager.py`)
The `StateManager` tracks pipeline DAG progression. It treats the `❌` (FAILED) status as a terminal state. Failed nodes are permanently marked, preventing the queue from recursively attempting to process fundamentally broken files unless explicitly overridden with `--force`.
