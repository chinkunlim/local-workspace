# Open Claw PKMS — User Manual

> **System Version**: V8.1 (Antigravity Checkpoint)
> **Status**: Production-Grade Headless CLI Deployment
> **Last Updated**: 2026-05-01

---

## Quick Start (TL;DR)

```bash
# Step 1: Start all services
cd ~/Desktop/local-workspace
./infra/scripts/start.sh

# Step 2: Drop your files into the universal inbox
cp lecture.m4a  open-claw-sandbox/data/raw/YourSubject/
cp textbook.pdf open-claw-sandbox/data/raw/YourSubject/

# Step 3: Wait — the system processes files automatically.
# When complete, your notes appear in:
open open-claw-sandbox/data/wiki/YourSubject/

# Step 4: Shutdown
./infra/scripts/stop.sh
```

That's it. The rest of this manual explains what happens in between and how to use advanced features.

---

## Part 1: How the System Works

### The Three-Layer Data Flow

```
YOU
 │
 ▼
📥 data/raw/<YourSubject>/        ← The ONLY folder you need to touch
 │   Drop .m4a or .pdf files here
 │
 ▼  (inbox_daemon routes automatically, 24/7)
 │
 ├──► 🏭 audio_transcriber        (for .m4a / .mp3)
 │         6-phase pipeline:
 │         P0: Build glossary
 │         P1: Transcribe with MLX-Whisper
 │         P2: Proofread with LLM
 │         P3: Merge segments
 │         P4: Highlight key concepts
 │         P5: Synthesise into study notes
 │
 └──► 🏭 doc_parser               (for .pdf)
           7-phase pipeline:
           P00a: Security check & metadata
           P01a: Extract text with Docling
           P01b: Detect and caption charts
           P01c: OCR quality gate
           P01d: Analyse figures with VLM
           P02: Highlight key concepts
           P03: Synthesise into study notes
 │
 ▼
🧠 data/wiki/<YourSubject>/       ← Your Obsidian Vault (final output)
```

### What is `data/raw/`?

This is your **only manual input point**. You never need to touch any other data directory. Simply:

1. Create a subfolder named after your subject: `data/raw/Cognitive_Psychology/`
2. Drop your files in: `data/raw/Cognitive_Psychology/lecture01.m4a`
3. The system detects the file and starts processing automatically.

### What is `data/wiki/`?

This is your finished knowledge base. Open it as an Obsidian vault to get:
- Bi-directional `[[WikiLinks]]` between related concepts
- Mermaid mind maps embedded in each note
- Cornell-format lecture notes with YAML metadata
- Highlighted key terms and definitions

---

## Part 2: Starting and Stopping

### Start All Services

```bash
cd ~/Desktop/local-workspace
./infra/scripts/start.sh
```

This launches:
1. **Ollama** — local LLM inference engine
2. **LiteLLM** — OpenAI-compatible proxy (port 4000)
3. **Open WebUI** — Chat UI at `http://localhost:3000`
4. **Pipelines** — Pipeline runner (port 9099)
5. **Inbox Daemon** — 24/7 file watcher on `data/raw/`
6. **RAM Watchdog** — Monitors memory; throttles tasks if RAM drops below 15%

### Check Service Status

```bash
./ops/check.sh
```

### Stop All Services

```bash
./infra/scripts/stop.sh
```

---

## Part 3: Processing Files Manually

While the inbox daemon runs automatically, you can also trigger pipelines manually via CLI.

### Audio Transcriber

```bash
cd open-claw-sandbox

# Process all pending audio files
python3 skills/audio_transcriber/scripts/run_all.py --process-all

# Process only one subject
python3 skills/audio_transcriber/scripts/run_all.py --subject Cognitive_Psychology

# Resume after an interruption
python3 skills/audio_transcriber/scripts/run_all.py --process-all --resume

# Force re-run (even completed files)
python3 skills/audio_transcriber/scripts/run_all.py --process-all --force

# Start from a specific phase (e.g., phase 2)
python3 skills/audio_transcriber/scripts/run_all.py --from 2

# Regenerate glossary only
python3 skills/audio_transcriber/scripts/run_all.py --glossary
```

### Doc Parser

```bash
cd open-claw-sandbox

# Process all pending PDFs
python3 skills/doc_parser/scripts/run_all.py --process-all

# Process only one subject
python3 skills/doc_parser/scripts/run_all.py --subject AI_Papers

# Force re-run
python3 skills/doc_parser/scripts/run_all.py --process-all --force
```

### Knowledge Compiler

Compiles all skill outputs into your Obsidian Vault with bi-directional WikiLinks:

```bash
cd open-claw-sandbox

python3 skills/knowledge_compiler/scripts/run_all.py --process-all
```

### Telegram Knowledge Base Agent

```bash
cd open-claw-sandbox

# Rebuild the vector index (run after new notes are generated)
python3 skills/telegram_kb_agent/scripts/indexer.py

# Start the Telegram bot daemon
python3 skills/telegram_kb_agent/scripts/bot_daemon.py
```

### Academic & Education Assistant

```bash
cd open-claw-sandbox

# Place files to compare inside:
# data/academic_edu_assistant/input/<YourSubjectName>/

# Run the comparison + Anki card generation
python3 skills/academic_edu_assistant/scripts/run_all.py
```

### Interactive Reader (In-Note AI Annotations)

Write a tag anywhere inside a Markdown note:
```markdown
> [AI: Summarise the key argument in this section]
```

Then run:
```bash
cd open-claw-sandbox
python3 skills/interactive_reader/scripts/run_all.py --process-all
```

The AI response is appended below the tag automatically.

---

## Part 4: PDF Routing Rules

PDFs can be routed in three different ways depending on their content:

| Mode | Behaviour |
|---|---|
| `audio_ref` | PDF is sent to `audio_transcriber` as a proofreading reference only |
| `doc_parser` | PDF is fully extracted by `doc_parser` |
| `both` | PDF is sent to BOTH simultaneously |

### View Current Routing Rules

```bash
cd open-claw-sandbox
python3 skills/inbox_manager/scripts/query.py --list
```

### Add a New Rule

```bash
python3 skills/inbox_manager/scripts/query.py --add "_slides" --routing audio_ref --description "Lecture slides"
python3 skills/inbox_manager/scripts/query.py --add "_textbook" --routing both --description "Course textbook"
```

### Remove a Rule

```bash
python3 skills/inbox_manager/scripts/query.py --remove "_slides"
```

---

## Part 5: Checking Progress

### Check Pipeline Progress

Each skill writes a checklist to its state directory:

```bash
# Audio transcriber progress
cat open-claw-sandbox/data/audio_transcriber/state/checklist.md

# Doc parser progress
cat open-claw-sandbox/data/doc_parser/state/checklist.md
```

### Check System Logs

```bash
# Tail the inbox daemon log
tail -f open-claw-sandbox/logs/openclaw.log

# Check all logs
ls open-claw-sandbox/logs/
```

---

## Part 6: Obsidian Vault Setup

1. Open **Obsidian** → `Open folder as vault`
2. Navigate to: `~/Desktop/local-workspace/open-claw-sandbox/data/wiki/`
3. Enable the **Mermaid** plugin for mind map rendering
4. Enable **Dataview** (optional) for dynamic note queries

Your knowledge base is fully structured with:
- YAML frontmatter for filtering and queries
- Mermaid mind maps for visual learning
- `[[WikiLinks]]` for concept network navigation
- Cornell-format tables for structured review

---

## Part 7: Troubleshooting

| Problem | Solution |
|---|---|
| Files not processing automatically | Check if `infra/scripts/start.sh` was run; verify `data/raw/` has files |
| LLM timeout / slow processing | Normal for large files; check `data/<skill>/state/checklist.md` for progress |
| `ModuleNotFoundError: No module named 'core'` | Run scripts from inside `open-claw-sandbox/` directory |
| Out of memory / system freeze | Lower the Ollama context window in `config.yaml`; ensure `watchdog.sh` is running |
| Corrupted state file | Delete `data/<skill>/state/` and re-run with `--force` |
| Need to re-process a specific file | Use `--file <filename> --force` flag |

---

## Part 8: Monorepo Structure Reference

```
local-workspace/
├── open-claw-sandbox/    ← Main application (all skill code lives here)
│   ├── core/             ← Shared framework (do not edit unless necessary)
│   ├── skills/           ← Individual skill pipelines
│   ├── data/             ← Runtime data (gitignored)
│   │   ├── raw/          ← 📥 YOUR INPUT FOLDER
│   │   └── wiki/         ← 🧠 YOUR OUTPUT (Obsidian Vault)
│   └── tests/            ← Unit tests
│
├── infra/
│   ├── scripts/
│   │   ├── start.sh      ← Start everything
│   │   └── stop.sh       ← Stop everything
│   ├── litellm/          ← LLM proxy config
│   ├── open-webui/       ← Chat interface
│   └── pipelines/        ← Pipeline plugins
│
├── docs/                 ← System documentation
└── memory/               ← AI agent memory & architecture docs
```
