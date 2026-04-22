# Open Claw — Operator's Manual

> **System Version**: V2 (Antigravity Checkpoint)  
> **Status**: Production-Grade Headless Deployment

Welcome to the Open Claw ecosystem. This manual provides pragmatic, step-by-step instructions for operating the Personal Knowledge Management System (PKMS) via its standardized interfaces: CLI, Telegram, Obsidian, and Open WebUI.

---

## 1. Unified CLI Operations

The Open Claw core utilizes a standardized CLI parser (`core/cli.py`) across all internal skills. You can trigger any skill manually using the `run_all.py` script located within its respective directory.

### Standard Pipeline Invocation
```bash
# Run the Doc Parser pipeline interactively (default)
python3 skills/doc-parser/scripts/run_all.py

# Run in Headless Batch Mode (Processes all pending files automatically)
python3 skills/doc-parser/scripts/run_all.py --process-all

# Target a specific subject taxonomy
python3 skills/audio-transcriber/scripts/run_all.py --subject "Philosophy"

# Force regeneration (bypass idempotency caches)
python3 skills/doc-parser/scripts/run_all.py --force --file "Kant_Critique.pdf" --single

# Output structured JSON logs (ideal for parsing or ELK integration)
python3 skills/doc-parser/scripts/run_all.py --process-all --log-json
```

---

## 2. Headless Telegram Operations

Open Claw is designed to run silently in the background. The `BotDaemon` provides asynchronous command-and-control capabilities via Telegram, allowing you to orchestrate the pipeline remotely without risking RAM exhaustion.

### Essential Commands
- `/status` — Polls the `SystemInboxDaemon` and returns the real-time DAG state of all queues.
- `/run` — Dispatches a global pipeline execution. The `LocalTaskQueue` guarantees that skills run sequentially, mitigating Ollama OOM crashes.
- `/pause` — Gracefully interrupts the current pipeline by transmitting a `SIGTERM`, safely saving progress to checkpoints before releasing VRAM.
- `/query <text>` — Executes a semantic RAG query against the ChromaDB vector store.

---

## 3. Obsidian YAML Workflow (Bidirectional Integration)

Open Claw integrates deeply with your local Obsidian vault. You can manipulate the state of your notes directly from Obsidian, triggering background synthesis pipelines.

### Triggering the `note-generator` (Rewrite Workflow)
1. Open any generated Markdown file within your Obsidian vault.
2. Locate the YAML frontmatter at the top of the file.
3. Modify the status line:
   ```yaml
   ---
   status: rewrite
   ---
   ```
4. Save the file.
5. The `SystemInboxDaemon` (via Watchdog) will instantly detect the atomic write. It will safely lock the file, transition the state to `status: processing`, and enqueue the `note-generator` skill to synthesize a refined version of your note (`*_rewrite.md`).

---

## 4. Open WebUI & Literature Matrix Synthesis

The true power of the Open Claw ecosystem lies in transforming raw extractions into higher-order knowledge architectures using Open WebUI.

### Synthesizing a Literature Matrix
When you have processed multiple papers via the `doc-parser`, you can synthesize them into a unified "Literature Matrix" for cross-referencing.

1. **Ensure the Pipeline is Complete**: Verify via `/status` that your target PDFs have reached Phase 1d (VLM parsing complete).
2. **Access Open WebUI**: Navigate to `localhost:8080`.
3. **Select the Knowledge Compiler Model**: Choose the `knowledge-compiler` profile (which enforces strict `temperature: 0` determinism).
4. **Attach Context**: Use the `#` command in Open WebUI to pull the compiled `content.md` files from your `data/doc-parser/output/05_Final_Knowledge/` directories.
5. **Prompt Execution**: Issue your synthesis command:
   > "Extract a Literature Matrix comparing the methodologies and constraints of the attached papers. Structure the output as a Markdown table."
6. **Result**: The deterministic model will analyze the perfectly parsed, un-hallucinated intermediate representations and yield a production-grade comparison matrix.

## 全域通知與儀表板標準化 (Universal Notification & Unified Dashboard)

在最新版本的 Open Claw 生態系中，所有的 Skill（包含語音轉錄、文件解析、知識編譯等）都已經實作了**全域標準化介面**：
1. **統一的儀表板**：所有模組在啟動時，皆會渲染統一格式的「📊 [技能名稱] 狀態與 DAG 追蹤面板」，讓您能在終端機中獲得完全一致的操作體驗。
2. **優雅中斷與通知**：您隨時可以透過 `Ctrl+C` 中斷正在執行的任務。系統會攔截 `KeyboardInterrupt`，不僅安全儲存當前狀態，還會透過 macOS 原生系統發送「Execution Interrupted」推播通知；當任務正常跑完時，也會發送「Pipeline 執行完畢」通知。
