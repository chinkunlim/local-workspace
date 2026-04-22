# Open Claw — Changelog

All notable changes to the Open Claw ecosystem will be documented in this file.

## [2.0.0] - 2026-04-22 ("Antigravity" Checkpoint)

### Architecture
- **Headless Migration**: Deprecated and removed legacy Flask WebUI components in favor of a resilient background daemon architecture.
- **LocalTaskQueue (RAM Guard)**: Introduced a strictly single-threaded global queue (`core/task_queue.py`) with `run_pipelines.lock`. Completely eliminates concurrent Model initialization and OS-level Out-Of-Memory (OOM) crashes.
- **Dead Letter Quarantine (DLQ)**: Implemented advanced failure isolation. Poisonous payloads that exceed `max_retries=3` or cause deterministic faults are intercepted and relocated to `data/quarantine/` with robust telemetry.
- **Data Flow Decoupling**: Extracted high-level synthesis logic out of `audio-transcriber` and `doc-parser` into dedicated synthesis skills (`note-generator`, `smart-highlighter`).

### Core & Observability
- **DRY Modularity**: Unified redundant filesystem operations into `core/file_utils.py` (`safe_read_json`, `managed_tmp_dir`, `ensure_dir`).
- **Structured Telemetry**: Integrated `JsonFormatter` into `core/log_manager.py`. Toggled via `OPENCLAW_LOG_JSON=1`, enabling seamless upstream log aggregation for headless operations.
- **Deterministic Exception Tracking**: Enforced `exc_info=True` across all critical exception handlers in `SystemInboxDaemon` and `StateManager` to eradicate silent fault swallowing.
- **Automated Validation**: Bootstrapped the foundational `pytest` suite within `tests/` to guarantee invariants for core subsystems (`AtomicWriter`, `ResumeManager`, etc.).
- **UI & UX**: `feat(global): standardized notification and UI across all skill modules`.

### Ecosystem Integrations
- **LiteLLM & ChromaDB**: Finalized integrations for semantic RAG routing.
- **Obsidian Bidirectional Sync**: Engineered atomic debouncing (`watchdog`) capable of triggering background refinement pipelines via Obsidian YAML metadata updates (`status: rewrite`).

### Anti-Hallucination & Model Safety
- **Strict Temperature Enforcement**: Hardcoded `temperature: 0` inside `knowledge-compiler` and `interactive-reader` configs to eliminate non-deterministic hallucinations.
- **VLM Pipeline Hardening**: Overhauled `p01d_vlm_vision.py` to dynamically index Markdown tables, handle missing images gracefully, and execute atomic commits.
- **VAD Safety Valve**: Enhanced `p01_transcribe.py` with `pydub.silence`. Introduced a failsafe `max_removal_ratio` trigger to automatically fall back to the raw audio if aggressive VAD thresholds mutilate the context.

## [1.0.0] - Initial Release
- Monolithic Flask-based architecture.
- Basic Audio and Document pipelines.
