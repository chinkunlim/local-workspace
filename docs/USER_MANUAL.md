# Open Claw Knowledge Ecosystem: Comprehensive Operator's Manual

> **System Version**: V2 (Antigravity Checkpoint)  
> **Status**: Production-Grade Headless Deployment

Welcome to your "Personal AI Second Brain"! This system operates entirely on your local machine, ensuring extreme privacy and high customizability.

This manual is divided into two sections: **[Part 1] Daily Operational Concepts** and **[Part 2] Complete CLI Operations**.

---

# Part 1: Daily Operational Concepts

## 🚀 1. System Initialization and Shutdown

```bash
cd ~/Desktop/local-workspace

# Start all core services
./infra/scripts/start.sh

# Gracefully terminate all services
./infra/scripts/stop.sh
```

The startup script automatically executes the following:
1. Enables anti-sleep mode (`caffeinate`) to protect long-running computational tasks.
2. Initializes Ollama, LiteLLM, and the underlying AI Pipelines.
3. Launches the Open Claw API Gateway (Port 18789).
4. Starts the `inbox_daemon` for 24/7 monitoring of your universal inbox.

---

## 🌊 2. Core Architecture: The Three Phases of Knowledge Flow

```
Your Raw Files
    │
    ▼
📥 data/raw/<Subject_Taxonomy>/          ← The ONLY manual entry point
    │ (Auto-dispatched by inbox_daemon)
    ├──► 🏭 data/audio-transcriber/      (Audio Factory Floor)
    └──► 🏭 data/doc-parser/             (PDF Factory Floor)
                │
                ▼ (Automated Output)
    🧠 data/wiki/<Subject_Taxonomy>/     ← Obsidian Vault (Final Synthesis)
```

### 📥 Phase 1: Universal Inbox
- **Path**: `open-claw-sandbox/data/raw/<Subject_Taxonomy>/`
- **Purpose**: This is the **only directory** where you need to manually drop files.
- **Rule**: Create subdirectories named after the subject, e.g., `data/raw/Cognitive_Psychology/`.

### 🏭 Phase 2: Invisible Factory Floors
- **Path**: `data/audio-transcriber/` and `data/doc-parser/`
- **Purpose**: Background processing zones. You do **not** need to manage any files here.

### 🧠 Phase 3: Obsidian Vault (The Brain)
- **Path**: `open-claw-sandbox/data/wiki/`
- **Purpose**: The final destination for all synthesized Markdown notes. This acts directly as your Obsidian Vault.

---

## 📄 3. PDF Extension Routing Rules

The `inbox_daemon` dynamically routes PDF files based on their filename suffixes. The rules are defined in `core/inbox_config.json`:

| Suffix Example | Routing Mode | Description |
|---|---|---|
| `L1_slides.pdf`, `L1_ref.pdf`, `L1_handout.pdf` | `audio_ref` | Used strictly as audio calibration references. **Does NOT** generate standalone notes. |
| `genetics_textbook.pdf`, `ch3_reading.pdf` | `both` | Sent to the `doc-parser` for standalone parsing **AND** used as an audio reference. |
| (No specific suffix) | `doc_parser` | Default behavior: Routed exclusively to the `doc-parser` pipeline. |

**Complete Suffix List (`audio_ref` mode)**:
`_ref`, `_refs`, `_slides`, `_slide`, `_handout`, `_handouts`, `_lecturenotes`, `_transcript`, `_worksheet`, `_supplement`, `_appendix`, `_coursework`, `課件`, `講義`, `參考`

**Complete Suffix List (`both` mode)**:
`_textbook`, `_book`, `_chapter`, `_ch`, `_reading`, `_readings`, `_material`, `_materials`, `_guide`, `_notes`

---

## 🤖 4. Mobile Access & Advanced Queries (Open Claw & Telegram)

### Headless Telegram Operations
Open Claw is designed to run silently in the background. The `BotDaemon` provides asynchronous command-and-control capabilities via Telegram, allowing remote orchestration without risking RAM exhaustion.
- `/status` — Polls the `SystemInboxDaemon` and returns the real-time DAG state of all queues.
- `/run` — Dispatches a global pipeline execution. The `LocalTaskQueue` guarantees sequential execution to mitigate Ollama OOM crashes.
- `/pause` — Gracefully interrupts the current pipeline (`SIGTERM`), safely saving checkpoints before releasing VRAM.
- `/query <text>` — Executes a semantic RAG query against the ChromaDB vector store.

### Open WebUI & Literature Matrix Synthesis
1. **Ensure the Pipeline is Complete**: Verify via `/status` that your target PDFs have reached Phase 1d (VLM parsing complete).
2. **Access Open WebUI**: Navigate to `localhost:8080`.
3. **Select the Knowledge Compiler Model**: Choose the `knowledge-compiler` profile (enforces strict `temperature: 0` determinism).
4. **Attach Context**: Use `#` to pull compiled `content.md` files from `data/doc-parser/output/05_Final_Knowledge/`.
5. **Prompt Execution**: "Extract a Literature Matrix comparing the methodologies and constraints of the attached papers. Structure the output as a Markdown table."

---

## 🔄 5. Full-Pipeline Integration Workflow (Obsidian ➡️ CLI ➡️ Open WebUI)

Open Claw interfaces collaborate seamlessly:
1. **Trigger (Obsidian)**: While reading `data/wiki/Cognitive_Psychology/lecture_01.md`, update the YAML frontmatter to `status: rewrite` and save.
2. **Automation (CLI Background Execution)**: `inbox_daemon` instantly detects the atomic write, locks the file (`status: processing`), and enqueues the `note_generator` skill. macOS native notifications (`osascript`) alert you to the pipeline's progress.
3. **High-Level Analysis (Open WebUI)**: Navigate to Open WebUI and query: "Generate a quiz based on my latest Cognitive Psychology notes." The AI utilizes RAG against your freshly synthesized vault.

---

# Part 2: Complete CLI Operations

> **Prerequisite**: Execute all commands from the root of the sandbox directory.
```bash
cd ~/Desktop/local-workspace/open-claw-sandbox
```

---

## 🎙️ CLI-1: Audio Transcription Pipeline (`audio-transcriber`)

**Standard Command Signature**:
```bash
python3 skills/audio-transcriber/scripts/run_all.py [OPTIONS]
```

### Basic Invocation
```bash
# Process all subjects and all audio files (Full Batch Mode)
python3 skills/audio-transcriber/scripts/run_all.py

# Target a specific subject taxonomy
python3 skills/audio-transcriber/scripts/run_all.py --subject "Cognitive Psychology"

# Target a specific file precisely
python3 skills/audio-transcriber/scripts/run_all.py     --subject "Cognitive Psychology"     --file lecture_01-1.m4a     --single

# Force regeneration (bypasses idempotency checkpoints)
python3 skills/audio-transcriber/scripts/run_all.py --force
```

### Checkpoint Resumption & Phase Control
```bash
# Resume from the last interrupted checkpoint
python3 skills/audio-transcriber/scripts/run_all.py --resume

# Start execution from a specific Phase (e.g., Phase 2 Calibration)
python3 skills/audio-transcriber/scripts/run_all.py --subject "Cognitive Psychology" --from 2
```

### Domain Glossary Management
```bash
# Auto-generate professional terminology glossary
python3 skills/audio-transcriber/scripts/run_all.py --subject "Cognitive Psychology" --glossary
```

---

## 📄 CLI-2: PDF Parsing Pipeline (`doc-parser`)

**Standard Command Signature**:
```bash
python3 skills/doc-parser/scripts/run_all.py [OPTIONS]
```

### Basic Invocation
```bash
# Scan inbox for pending PDFs without processing
python3 skills/doc-parser/scripts/run_all.py --scan

# Run in Headless Batch Mode (Processes all pending files)
python3 skills/doc-parser/scripts/run_all.py --process-all

# Target a specific subject taxonomy
python3 skills/doc-parser/scripts/run_all.py --subject "Cognitive Psychology"
```

---

## 🧠 CLI-3: Knowledge Compilation (`knowledge-compiler`)

Compiles outputs from all individual skills and publishes them into the `data/wiki/` Obsidian Vault with bidirectional links.
```bash
# Compile all subjects
python3 skills/knowledge-compiler/scripts/run_all.py
```

---

## ✏️ CLI-4: Smart Highlighting (`smart_highlighter`)

Injects AI-driven smart highlights (`==keyword==`) into any Markdown document.
```bash
python3 skills/smart_highlighter/scripts/highlight.py     --input-file data/wiki/Cognitive_Psychology/lecture_01.md     --output-file data/wiki/Cognitive_Psychology/lecture_01_highlighted.md
```

---

## 📝 CLI-5: Note Generator (`note_generator`)

Executes a Map-Reduce knowledge synthesis to output highly structured notes and Mermaid mind maps.
```bash
python3 skills/note_generator/scripts/synthesize.py     --subject "Cognitive Psychology"     --label "lecture_01"     --input-file data/wiki/Cognitive_Psychology/lecture_01.md     --output-file data/wiki/Cognitive_Psychology/lecture_01_summary.md
```

---

## 📋 CLI-6: Inbox Routing Management (`inbox-manager`)

Dynamically manages `core/inbox_config.json` routing constraints without manual JSON editing.
```bash
# List all active routing rules
python3 skills/inbox-manager/scripts/query.py list

# Add a custom routing rule for 'both' processing
python3 skills/inbox-manager/scripts/query.py add     --add _exam     --routing both     --description "Exam materials — parse + audio reference"
```

---

## 📖 CLI-7: Interactive Reader (`interactive-reader`)

Batch processes Obsidian notes containing `> [AI: ...]` markers and writes responses inline.
```bash
python3 skills/interactive-reader/scripts/run_all.py
```

---

## 🔬 CLI-8: Academic Educational Assistant (`academic-edu-assistant`)

Performs cross-document topic comparison and outputs Anki-formatted review flashcards.
```bash
python3 skills/academic-edu-assistant/scripts/run_all.py     --query "Compare the core assumptions of Behaviorism and Cognitivism"     --anki
```

---

## 🔔 Universal Notification & Unified Dashboard

All Open Claw skills integrate a standardized architectural interface:
1. **Preflight Checks**: Every orchestrator automatically executes a `✈️ Preflight Check` to validate dependencies, configurations, and connectivity (e.g. Ollama, `poppler-utils`) before processing begins.
2. **Unified Dashboard & Code Self-Healing**: Every module renders a standardized `📊 [Skill Name] State & DAG Tracking Panel` in the terminal for consistent UX. 
3. **Interactive Selection UI**: If you execute a pipeline without arguments, the Orchestrator will display an interactive CLI menu allowing you to use numbers and ranges (e.g. `1,3,5` or `1-5`) to select pending tasks, or even choose previously completed tasks for reprocessing.
4. **Graceful Interruptions & Notifications**: Press `Ctrl+C` to halt operations. The system intercepts `KeyboardInterrupt`, saves state checkpoints safely, and dispatches a macOS native alert (`Execution Interrupted`). Upon successful completion, a `Pipeline Execution Complete` notification is dispatched. **No additional software installation is required.**
