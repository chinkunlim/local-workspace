# OpenClaw Architecture & Engineering Stack Reference

> **Scope**: An exhaustive technical reference of the patterns, principles, and technology stack powering the OpenClaw PKMS and Multi-Agent Sandbox.
> **Generated**: 2026-05-05

---

## 1. Security & Defense Mechanisms
* **Path Traversal Defense**: Strict bounds checking (`os.path.abspath().startswith(WORKSPACE_DIR)`) on file paths before reading/writing to ensure Agents cannot escape the designated workspace (see `SecurityManager` and `AtomicWriter`).
* **Atomic Writes**: Utilizing `tempfile.mkstemp` and `os.replace` to perform crash-safe writes. Prevents file corruption (0-byte files) if the system crashes or OOMs during a write.
* **Idempotent Bootstrapping**: `bootstrap.py` securely and idempotently adds the core module to `sys.path` regardless of where the python script was invoked from.
* **PDF Security Check**: Pre-flight validation for allowed characters, size limits, and traversal attempts before handing binary files to the ingestion engines.

## 2. Resource & Hardware Management (RAM Guards)
* **System Telemetry**: Uses `psutil` to monitor real-time RAM, CPU Temperature, Disk space, and Battery levels.
* **Thermal Throttling & Graceful Pauses**: Triggers safe pauses when RAM < 500MB or CPU Temp > 85°C. Triggers emergency exit (with process termination) if critical thresholds are met (e.g., RAM < 200MB).
* **Sequential Task Queue (`LocalTaskQueue`)**: Enforces single-threaded processing for heavy LLM and VLM workloads. Eliminates concurrent model loading to prevent out-of-memory (OOM) explosions on Apple Silicon.
* **Model Unloading Protocol**: Explicit garbage collection (`gc.collect()`), cache clearing (`mx.clear_cache()`), and API directives (`keep_alive=0`) to forcibly purge VRAM after heavy generation tasks.

## 3. Data Integrity & Orchestration
* **DAG (Directed Acyclic Graph) State Tracking**: `state_manager.py` computes hashes of output files. If the hash of a Phase 1 file is unchanged, Phase 2 is skipped. Enables Makefile-like efficiency and resume capabilities.
* **Graceful Shutdown (Signal Handling)**: Intercepts `SIGINT` (Ctrl+C). First press yields a prompt to Pause/Stop gracefully (serializing the pipeline state to JSON). Second press forces exit.
* **Config Deep Merging**: `ConfigManager` recursively merges global infrastructure thresholds (`global.yaml`) with skill-specific logic (`config.yaml`), upholding DRY principles.

## 4. AI Quality & Anti-Hallucination
* **Zero Temperature Mandate**: All production generations use `temperature: 0` for determinism.
* **Triple Defense Anti-Hallucination Pipeline**:
    1.  **Layer 0 (API Native)**: E.g., Disabling `condition_on_previous_text` in Whisper to stop auto-regressive hallucinations.
    2.  **Layer 1 (Acoustic/VAD)**: Pre-stripping absolute silence using `pydub` to give the model clean input.
    3.  **Layer 2 (Algorithmic)**: Using N-gram overlap and **zlib compression ratio heuristics** to detect repetitive hallucination loops, triggering localized temperature-bumped retries.
* **Time-Based Chunk Fallback**: Automatically slicing runaway continuous audio (where VAD fails) into 30s deterministic chunks to save memory.
* **Circuit Breaker Pattern**: If primary heavy models (e.g., Qwen 14B) timeout or fail 3 times, the system automatically falls back to a lighter, faster model (e.g., Gemma 4B).

## 5. Software Engineering Principles (SOLID & DRY)
* **Single Responsibility Principle (SRP)**: Clear separation of duties. `audio_transcriber` only transcribes. `smart_highlighter` only highlights.
* **Open/Closed Principle (OCP)**: `PipelineBase` runs the show. New capabilities are added by creating new Skills in the registry, not by hacking the core.
* **Dependency Inversion Principle (DIP)**: `llm_client`, `state_manager`, and `telegram_bot` are injected into `PipelineBase`, making it highly testable and loosely coupled.
* **DRY (Don't Repeat Yourself)**: `run_skill_pipeline` serves as the universal template method for all orchestrators. CLI parsing, DAG checking, and logging are written exactly once.
* **Fail-Fast**: Configuration validators crash the program on boot (`ConfigValidator.require()`) if an API URL or critical setting is missing, rather than failing mid-pipeline.

## 6. Multi-Agent & RAG Architectures
* **Persona Isolation**: Using specialized models for specific tasks (e.g., DeepSeek-R1 for `feynman_simulator` debates, Gemma for RAG queries).
* **AI Gateway (LiteLLM)**: Abstracting the vendor layer. Code requests a "generation", and the gateway handles whether it hits local Ollama or cloud providers.
* **ChromaDB & GraphRAG**: Implicit knowledge graphs and vector embeddings for contextual retrieval.
* **Human-in-the-Loop (HITL)**: Asynchronous event suspension. The pipeline serializes state to disk, throws an interrupt, and pings the user via Telegram for approval before continuing dangerous/ambiguous tasks.

## 7. Toolchain & Python Language Features
* **Code Quality**: `Ruff` (ultra-fast Rust-based linting/formatting) and `Mypy` (strict static type checking).
* **Data Structures**: `@dataclass` for clean data definitions (`PipelineResponse`, `HITLEvent`).
* **Concurrency**: `Generators (yield)` to stream data without loading full files into RAM.
* **Low-Level Hacks**: `os.dup2` and file descriptor redirection to silence C-level standard error output from third-party libraries.
* **Media Processing**: `pydub`, `faster-whisper`, `mlx-whisper`.
* **CLI/UX**: `tqdm` (progress bars), `rich` (spinners/colors), `osascript` (macOS native push notifications).

## 8. Version Control & DevOps
* **SSoT (Single Source of Truth) Documentation**: Strict governance over `ARCHITECTURE.md` and `DECISIONS.md`. Abandoned concepts are labeled `[ABANDONED]`, never deleted.
* **Git Hygiene**: `.gitignore` strategies to exclude VRAM caches, DB files, and secrets (`.env`). Conventional Commits format enforced.
* **Daemon Processes**: `inbox_daemon.py` and `watchdog.sh` for event-driven architecture, moving away from manual script execution to background automation.
