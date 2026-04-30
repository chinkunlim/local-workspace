import os

docs_dir = "/Users/limchinkun/Desktop/local-workspace/docs"
sandbox_dir = "/Users/limchinkun/Desktop/local-workspace/open-claw-sandbox"

# 1. Update INFRA_SETUP.md
with open(os.path.join(sandbox_dir, "AGENTS.md")) as f:
    agents_content = f.read()

with open(os.path.join(docs_dir, "INFRA_SETUP.md"), "a") as f:
    f.write("\n\n# Multi-Agent Orchestration Framework (v1.2.0 Update)\n\n")
    f.write(
        "This system has been upgraded from a single-script collection to a multi-agent orchestration framework.\n\n"
    )
    f.write("## Router Agent & Intent Decomposition\n")
    f.write(
        "The `core/router_agent.py` uses an LLM-based DAG parser to break down natural language intents into a sequential pipeline of skill executions.\n"
    )
    f.write(agents_content)

# 2. Update ARCHITECTURE.md
with open(os.path.join(docs_dir, "ARCHITECTURE.md"), "a") as f:
    f.write("\n\n# Multi-Agent Architecture (v1.2.0)\n")
    f.write(
        "- `core/`: The heart of the system. Manages state (`state_manager`), queues (`task_queue`), config (`config_manager`), and LLM connections (`llm_client`).\n"
    )
    f.write(
        "- `infra/pipelines/`: Interface layer connecting external providers (OpenAI, Anthropic) and tools.\n"
    )
    f.write(
        "- `skills/`: The concrete business logic implementation. Each skill has its own `config/`, `scripts/`, and `docs/`.\n"
    )

# 3. Update USER_MANUAL.md
with open(os.path.join(docs_dir, "USER_MANUAL.md"), "a") as f:
    f.write("\n\n# Use-Case Driven Operations (v1.2.0)\n\n")
    f.write("## Telegram Bot Integration\n")
    f.write(
        "The Telegram bot provides real-time notifications for Human-in-the-Loop (HITL) events. When the system encounters low confidence data, it will pause and message you. Reply with `/hitl approve <trace_id>` to resume.\n\n"
    )
    f.write("## Configuring Providers\n")
    f.write(
        "Configure your LLM providers in `config.yaml` or global `~/.openclaw/openclaw.json`. The new `llm_client` automatically falls back to secondary models upon encountering rate limits.\n"
    )

# 4. Update CODING_GUIDELINES.md
with open(os.path.join(docs_dir, "CODING_GUIDELINES.md"), "a") as f:
    f.write("\n\n## 🚨 P4 Sprint: Multi-Agent Architecture Rules (v1.2.0+)\n\n")
    f.write("1. **Mandatory Async (強制非同步)**\n")
    f.write(
        "   - All external network requests (LLM API, Database) MUST use `asyncio` and `aiohttp`.\n"
    )
    f.write(
        "   - Sequential processing of batches (like chunking in `doc_parser` or `audio_transcriber`) should utilize `async_batch_generate` with an `asyncio.Semaphore` to maximize throughput without causing OOM.\n\n"
    )
    f.write("2. **State Immutability (狀態不可變性)**\n")
    f.write(
        "   - During Pipeline execution, state objects (e.g., JSON files in `state/`) must NOT be mutated in-place by external scripts.\n"
    )
    f.write("   - Use atomic operations (`core/atomic_writer.py`) and write new copies.\n")
    f.write(
        "   - For `MemoryPool` global state, use the built-in locking provided by `StateManager`.\n\n"
    )
    f.write("3. **Unified Logging (統一日誌)**\n")
    f.write("   - `print()` is strictly forbidden in core pipeline logic.\n")
    f.write(
        "   - All standard output must flow through `PipelineBase.log()`, `info()`, `warning()`, or `error()`.\n"
    )
    f.write(
        "   - Use `rich` for formatting terminal output (spinners, progress bars, colored text) in `cli_runner.py` or interactive scripts.\n"
    )

# 5. Consolidate CHANGELOG.md
root_changelog = os.path.join("/Users/limchinkun/Desktop/local-workspace", "CHANGELOG.md")
sandbox_changelog = os.path.join(sandbox_dir, "CHANGELOG.md")

if os.path.exists(sandbox_changelog):
    with open(sandbox_changelog) as f:
        sandbox_content = f.read()
    with open(root_changelog, "a") as f:
        f.write("\n\n")
        f.write("## [v1.2.0] - 2026-04-30 Multi-Agent Architecture Update\n")
        f.write("- **Added**: Global State & Memory Pool via `MemoryPool` in `state_manager.py`.\n")
        f.write(
            "- **Added**: Dynamic Routing & Task Decomposition via `RouterAgent` LLM parsing.\n"
        )
        f.write(
            "- **Added**: HITL Pipeline Resumption with `HITLPendingInterrupt` checkpointing.\n"
        )
        f.write("- **Added**: Fully Async LLM Generation using `aiohttp` and `tenacity`.\n")
        f.write("- **Added**: `rich`-based terminal UI formatting.\n")
        f.write("\n### Legacy Sandbox Changelog\n\n")
        f.write(sandbox_content)
    os.remove(sandbox_changelog)
