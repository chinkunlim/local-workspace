# Open Claw PKMS — User Manual

> **System Version**: V9.1 (Performance & Robustness Hardening)
> **Status**: Production-Grade Headless CLI Deployment
> **Last Updated**: 2026-05-04

---

## Quick Start (TL;DR)

```bash
# Step 1: Start all services
cd ~/Desktop/local-workspace
./infra/scripts/start.sh

# Step 2: Drop your files into the universal inbox
cp lecture.m4a  open-claw-sandbox/data/raw/YourSubject/
cp textbook.pdf open-claw-sandbox/data/raw/YourSubject/

# Step 3: Wait — the system parses your intent and routes files automatically.
# Through the magic of the RouterAgent and EventBus, your file will be processed through
# extraction, note generation, and knowledge compilation automatically.
# When complete, your notes appear in:
open open-claw-sandbox/data/wiki/YourSubject/

# Step 4: Shutdown
./infra/scripts/stop.sh
```

That's it. The rest of this manual explains what happens in between, how the system routes files, and how to interact with Human-in-the-Loop gates.

---

## Part 1: How the System Works (V8.2 Intent-Driven Architecture)

### The Fully Automated Data Flow

Open Claw now uses an **Intent-Driven RouterAgent** and an **EventBus** to automatically chain multiple skills together. You no longer need to trigger downstream processing manually.

```mermaid
graph TD
    A[📥 Drop file in data/raw/Subject] --> B[👁️ Inbox Daemon (File Stabilisation)]
    B --> C[🗺️ RouterAgent (Intent Resolution + Model Selection)]

    C -- "Low Complexity → qwen2.5-coder:7b" --> D[🎧 audio_transcriber]
    C -- "Low Complexity → qwen2.5-coder:7b" --> E[📄 doc_parser]
    C -- "High Complexity → deepseek-r1:14b" --> F_[🧠 feynman_simulator]

    D -- "Event: PipelineCompleted" --> F[📝 note_generator]
    E -- "Event: PipelineCompleted" --> F

    F -- "Event: PipelineCompleted" --> G[🧠 knowledge_compiler]
    G --> H[📚 Obsidian Vault (data/wiki)]
```

### What is `data/raw/`?

This is your **only manual input point**. You never need to touch any other data directory. Simply:

1. Create a subfolder named after your subject: `data/raw/Cognitive_Psychology/`
2. Drop your files in:
   - Audio: `lecture01.m4a`
   - PDF: `textbook.pdf`
   - Video: `class_recording.mp4` (or `.mov`, `.mkv`)
3. The `inbox_daemon` detects the file, waits for it to stabilize (debounce), and hands it to the `RouterAgent`.
4. The `RouterAgent` resolves the required Skill Chain (e.g. `[audio_transcriber, note_generator, knowledge_compiler]`) and enqueues the first task.
5. As each skill successfully completes, it fires a `PipelineCompleted` event, which automatically triggers the next skill in the chain.

### What is `data/wiki/`?

This is your finished knowledge base. Open it as an Obsidian vault to get:
- Bi-directional `[[WikiLinks]]` between related concepts
- Mermaid mind maps embedded in each note
- Cornell-format lecture notes with YAML metadata
- `[[WikiLinks]]` for concept network navigation
- Cornell-format lecture notes with YAML metadata
- Highlighted key terms and definitions
- **Cross-Semester Semantic Links**: related past notes automatically injected via ChromaDB similarity search
- Embedded FFmpeg keyframes interleaved with audio transcripts (for video ingestions)

---

## Part 2: Context-Aware Model Routing (V9.1)

The `RouterAgent` now automatically selects the optimal local LLM based on the **complexity** of the task. You do **not** need to configure this manually — it is fully transparent to you.

| Task Complexity | Intent Keywords | Model Used | Why |
|:---|:---|:---|:---|
| **Low** | `auto`, `transcribe`, `parse`, `compile` | `qwen2.5-coder:7b` | Fast, low VRAM, suitable for structured extraction |
| **High** | `debate`, `research`, `feynman`, `analyze`, `deep`, `study` | `deepseek-r1:14b` | Deep reasoning required for Socratic debate and academic verification |

**How to observe model selection in logs:**
```bash
# Watch the RouterAgent routing decisions in real-time
tail -f open-claw-sandbox/logs/task_queue.log | grep "Model:"

# Or simulate the routing decision directly:
cd open-claw-sandbox
export WORKSPACE_DIR="$(pwd)"
export PYTHONPATH="$(dirname $(pwd)):$(pwd):$PYTHONPATH"

python3 - <<'EOF'
from core.orchestration.router_agent import RouterAgent, TaskManifest
router = RouterAgent()

# Low Complexity
m1 = TaskManifest(source_path="/tmp/test.m4a", intent="auto", subject="Physics")
router.resolve(m1)
print(f"auto → {m1.model}")

# High Complexity
m2 = TaskManifest(source_path="/tmp/test.md", intent="feynman debate", subject="Physics")
router.resolve(m2)
print(f"feynman debate → {m2.model}")
EOF
```

Expected output:
```
auto → qwen2.5-coder:7b
feynman debate → deepseek-r1:14b
```

---

## Part 3: Semantic Caching (V9.1)

To reduce redundant GPU computation, all LLM calls with `temperature=0` (deterministic) are automatically cached in a local SQLite database at:
```
open-claw-sandbox/data/llm_cache.sqlite3
```

**How it works:**
- On every LLM call, a `SHA-256` hash of `(model, prompt)` is computed.
- If a matching hash is found in the cache, the stored response is returned **instantly**, skipping inference entirely.
- If not found, the LLM is called normally, and the result is stored for future use.
- The cache is persistent across reboots — it accumulates over sessions.

**Log message when a cache hit occurs:**
```
⚡ 命中語意快取 (Semantic Cache)，跳過推理。
```

**To clear the cache (e.g., when prompts change significantly):**
```bash
rm open-claw-sandbox/data/llm_cache.sqlite3
```

---

## Part 4: Multimodal Video Ingestion

If you drop a video file (`.mp4`, `.mov`, `.mkv`) into `data/raw/`, the system automatically routes it to the `video_ingester` skill.
1. The system extracts high-quality screenshots (keyframes) every 30 seconds.
2. It transcribes the video's audio track.
3. It interleaves the screenshots with the text, creating an illustrated Markdown document.
4. The output is forwarded to `note_generator` and compiled into your Obsidian vault.

---

## Part 5: Spaced Repetition via Telegram

Open Claw includes a built-in **SuperMemo-2 (SM-2)** engine to help you retain knowledge. When you process academic notes, the system automatically generates Anki flashcards.

1. **Daily Push**: At 09:00 AM every day, the `scheduler` daemon checks for due cards and sends them to your connected Telegram account.
2. **Interactive Review**:
   - Reply to a card with `/reveal <card_id>` to view the answer.
   - Reply with `/rate <card_id> <0-5>` to score your memory (5 = Perfect, 0 = Forgot completely).
3. The SM-2 algorithm will automatically schedule the next review date based on your score.

---

## Part 6: Human-in-the-Loop (HITL) Verification Gates

Open Claw enforces strict GIGO (Garbage-In, Garbage-Out) prevention. Before allowing potentially hallucinated data to pollute your knowledge base, the system will pause and ask for your verification.

### How to use the Verification Gate

When a skill (like `audio_transcriber` Phase 2, or `academic_edu_assistant` Anki export) reaches a critical juncture, it will spawn a temporary Web UI and pause the pipeline:

1. You will see a terminal message like: `🌐 啟動 Human-in-the-Loop 驗證閘門: http://localhost:8080`
2. Open your browser and navigate to `http://localhost:8080`.
3. You will see a side-by-side diff:
   - **Left Side**: The original raw text (or source audio with click-to-play timestamps).
   - **Right Side**: The AI's proposed corrections or generated Anki cards.
4. Review the changes. You can manually edit the text on the right side if the AI made a mistake.
5. Click **"Approve & Resume Pipeline"**.
6. The web server shuts down instantly, and the pipeline resumes using your approved, high-integrity data.

---

## Part 7: Starting and Stopping

### Start All Services

```bash
cd ~/Desktop/local-workspace
./infra/scripts/start.sh
```

This launches:
1. **Ollama** — local LLM inference engine
2. **LiteLLM** — OpenAI-compatible proxy (port 4000)
3. **Open WebUI** — Chat UI at `http://localhost:3000`
4. **Inbox Daemon** — 24/7 file watcher on `data/raw/` (Includes RouterAgent)
5. **RAM Watchdog** — Monitors memory; throttles tasks if RAM drops below 15%

### Check Service Status

```bash
./ops/check.sh
```

### Stop All Services

```bash
./infra/scripts/stop.sh
```

---

## Part 8: Processing Files Manually (Advanced)

While the `RouterAgent` handles automatic chaining, you can also trigger pipelines manually via CLI. This is useful for forcing re-runs or resuming from checkpoints.

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
```

### Doc Parser

```bash
cd open-claw-sandbox

# Process all pending PDFs
python3 skills/doc_parser/scripts/run_all.py --process-all

# Process only one subject
python3 skills/doc_parser/scripts/run_all.py --subject AI_Papers
```

### Knowledge Compiler

Compiles all skill outputs into your Obsidian Vault with bi-directional WikiLinks. (Note: The RouterAgent usually triggers this automatically at the end of a chain).

```bash
cd open-claw-sandbox
python3 skills/knowledge_compiler/scripts/run_all.py --process-all
```

---

## Part 9: Checking Progress

### Task Queue Status
Because tasks are executed in a single-threaded queue with exponential backoff retry, you can view the queue activity in the inbox daemon logs:

```bash
tail -f open-claw-sandbox/logs/task_queue.log
```

**Key log patterns to watch for:**
| Log Message | Meaning |
|:---|:---|
| `▶️ [TaskQueue] 開始執行任務` | A skill pipeline has started |
| `✅ [TaskQueue] 任務成功完成` | A pipeline finished successfully |
| `🔄 [TaskQueue] 準備重試任務 (等待 Xs)` | Exponential backoff triggered; task will retry after X seconds |
| `☠️ [DLQ] 已隔離毒藥檔案` | A file failed 3 times and was moved to `data/quarantine/` |
| `⚡ 命中語意快取` | LLM call skipped due to cache hit |
| `🗺️ [RouterAgent] 接力觸發` | A pipeline handoff between skills occurred |

### Skill State Checklists
Each skill writes a persistent JSON/MD checklist to its state directory:

```bash
# Audio transcriber progress
cat open-claw-sandbox/data/audio_transcriber/state/checklist.md

# Doc parser progress
cat open-claw-sandbox/data/doc_parser/state/checklist.md
```

---

## Part 10: Obsidian Vault Setup

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

## Part 11: Troubleshooting

| Problem | Solution |
|---|---|
| Files not processing automatically | Check if `infra/scripts/start.sh` was run; verify `data/raw/` has files. Check `task_queue.log` for errors. |
| LLM timeout / slow processing | Normal for large files; check `data/<skill>/state/checklist.md` for progress. |
| `ModuleNotFoundError: No module named 'core'` | Run scripts from inside `open-claw-sandbox/` and ensure `WORKSPACE_DIR` and `PYTHONPATH` are set. |
| Out of memory / system freeze | The single-threaded `task_queue` should prevent this. If it happens, ensure `watchdog.sh` is running to throttle processes. |
| Corrupted state file | Delete `data/<skill>/state/` and re-run with `--force`. |
| File failed to process 3 times | Check `data/quarantine/<skill>/quarantine_log.json` for the error. Fix the root cause and copy the file back to `data/raw/`. |
| Semantic cache returning stale results | Delete `data/llm_cache.sqlite3` to clear all cached LLM responses. |

---

## Part 12: Monorepo Structure Reference

```
local-workspace/
├── open-claw-sandbox/    ← Main application (all skill code lives here)
│   ├── core/
│   │   ├── ai/           ← LLM Client with Semantic Cache (llm_cache.sqlite3)
│   │   ├── orchestration/ ← RouterAgent (Model Routing), TaskQueue (Exponential Backoff), EventBus
│   │   ├── services/     ← inbox_daemon, scheduler (SM-2), telegram_bot
│   │   └── state/        ← StateManager with fcntl locking (JsonBackend / RedisBackend)
│   ├── skills/           ← Individual skill plugins (dynamically loaded via manifest.py)
│   ├── data/             ← Runtime data (gitignored)
│   │   ├── raw/          ← 📥 YOUR INPUT FOLDER
│   │   ├── wiki/         ← 🧠 YOUR OUTPUT (Obsidian Vault)
│   │   ├── quarantine/   ← ☠️ Failed files (after 3 retry attempts)
│   │   └── llm_cache.sqlite3 ← ⚡ Semantic Cache
│   └── tests/            ← Unit tests
│
├── infra/
│   ├── scripts/          ← Start/Stop scripts
│   ├── litellm/          ← LLM proxy config
│   ├── open-webui/       ← Chat interface
│   └── pipelines/        ← Pipeline plugins
│
├── docs/                 ← System documentation
└── memory/               ← AI agent memory & architecture docs
```
