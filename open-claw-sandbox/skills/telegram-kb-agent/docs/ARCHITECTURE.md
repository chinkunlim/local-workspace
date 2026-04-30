# telegram-kb-agent — Architecture

## Role

`telegram-kb-agent` is the **mobile knowledge retrieval interface**. It provides two core services:
1. **Indexer** (`scripts/indexer.py`): Builds a ChromaDB vector store from `data/wiki/` notes.
2. **Bot Daemon** (`scripts/bot_daemon.py`): A long-running Telegram bot that answers user questions via RAG (Retrieval-Augmented Generation) against the ChromaDB index.

This skill is the user-facing "front door" to the entire knowledge pipeline.

## Design Principles

1. **Single Bot Token**: Only ONE instance of this daemon may run at a time. Multiple instances cause Telegram Long Polling conflicts. The daemon uses a PID lock file to enforce this.
2. **Index before Query**: The vector index must be built (or rebuilt) before the bot can answer questions. Index staleness (wiki updated but index not rebuilt) is the most common source of "outdated" answers.
3. **RAG over direct LLM**: Never answer from LLM knowledge alone. All answers are grounded in retrieved passages from the user's personal wiki vault.
4. **Open Claw native integration**: The bot daemon is managed by `core/services/telegram_bot.py`. Telegram token management is centralized; this skill only provides the query logic.

## Processing Flow

```
Indexer (one-shot, run after wiki updates):
  data/wiki/**/*.md
  │
  └── Chunk documents (smart_split)
        └── LLM Embedding → ChromaDB upsert
              └── data/doc-parser/output/vector_db/ (persistent index)

Bot Daemon (long-running):
  User → Telegram Message
  │
  └── core.services.telegram_bot receives message
        └── semantic_search(query, top_k=5, ChromaDB)
              └── Retrieved passages + LLM synthesis → Answer → Telegram reply
```

## Directory Structure

```
skills/telegram-kb-agent/
├── SKILL.md              ← Quick-start guide
├── docs/
│   ├── ARCHITECTURE.md   ← This file
│   ├── CLAUDE.md         ← AI agent collaboration context
│   └── DECISIONS.md      ← Technical decision log
└── scripts/
    ├── indexer.py        ← Builds/updates ChromaDB vector index from wiki
    ├── bot_daemon.py     ← Telegram bot long-polling handler
    └── query.py          ← CLI query interface (for testing without Telegram)
```

## CLI Commands

```bash
# Build or rebuild the vector index
python3 skills/telegram-kb-agent/scripts/indexer.py

# Start the Telegram bot daemon
python3 skills/telegram-kb-agent/scripts/bot_daemon.py

# Test RAG queries without Telegram (CLI interface)
python3 skills/telegram-kb-agent/scripts/query.py --query "What is Working Memory?"
```

## Telegram Bot Commands

| Command | Action |
|:---|:---|
| `/query <text>` | RAG search against the full wiki vault |
| `/status` | Returns pipeline status from `inbox_daemon` |
| `/run` | Triggers global pipeline execution |
| `/pause` | Gracefully interrupts current pipeline |
| `/hitl approve <trace_id>` | Resumes a HITL-paused pipeline |

## Dependencies

| Module | Purpose |
|:---|:---|
| `core.services.telegram_bot` | Telegram bot lifecycle management |
| `core.ai.hybrid_retriever` | ChromaDB semantic search |
| `core.ai.llm_client.OllamaClient` | Answer synthesis from retrieved passages |
