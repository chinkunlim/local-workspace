# CLAUDE.md — Telegram KB Agent Skill

> AI agent collaboration context for the `telegram-kb-agent` skill.
> Read this before touching the bot daemon, indexer, or ChromaDB configuration.

## Skill Summary

`telegram-kb-agent` is the user's mobile knowledge retrieval interface. It indexes `data/wiki/`
into ChromaDB and exposes a Telegram bot that answers RAG queries against the user's personal
knowledge base. It also serves as the HITL notification channel — all Human-in-the-Loop alerts
and `/hitl approve` commands flow through this skill's bot daemon.

## Key Invariants

1. **PID lock — single instance only**: Only one `bot_daemon.py` may run at any time. Telegram's Long Polling API rejects multiple simultaneous connections with the same token. The daemon creates a `.bot.pid` lock file and exits if it finds one.
2. **Never answer from LLM memory alone**: All responses must be grounded in retrieved ChromaDB passages. If ChromaDB returns no results, respond with "No relevant notes found" — do NOT fall back to hallucinated LLM knowledge.
3. **Rebuild index after wiki updates**: The ChromaDB index is NOT automatically updated when `knowledge-compiler` publishes new notes. Operators must manually run `indexer.py` after compilation.
4. **HITL integration**: The `/hitl approve <trace_id>` Telegram command writes a resume signal to `core/state/` that the paused pipeline polls. This is the critical recovery mechanism for interrupted pipelines — never disable or bypass it.
5. **Telegram token in env only**: The bot token must come from `TELEGRAM_BOT_TOKEN` env variable. Never hardcode it. The `.env` file is gitignored.

## File Locations

| Item | Path |
|:---|:---|
| Bot daemon | `skills/telegram-kb-agent/scripts/bot_daemon.py` |
| Indexer | `skills/telegram-kb-agent/scripts/indexer.py` |
| CLI query tool | `skills/telegram-kb-agent/scripts/query.py` |
| Architecture doc | `skills/telegram-kb-agent/docs/ARCHITECTURE.md` |

## CLI Usage

```bash
# Rebuild the ChromaDB index from wiki vault
python3 skills/telegram-kb-agent/scripts/indexer.py

# Start the bot daemon (blocks — run in background or via start.sh)
python3 skills/telegram-kb-agent/scripts/bot_daemon.py

# Test a query without Telegram
python3 skills/telegram-kb-agent/scripts/query.py --query "What is Working Memory?"
```

## Required Environment Variables

```bash
TELEGRAM_BOT_TOKEN=<your-bot-token>          # From @BotFather
TELEGRAM_CHAT_ID=<your-chat-id>              # Your personal Telegram user ID
OPENCLAW_API_URL=http://127.0.0.1:18789      # Open Claw API gateway
```

## Common Agent Tasks

**Index is stale (bot giving outdated answers)**:
```bash
python3 skills/telegram-kb-agent/scripts/indexer.py
```

**Bot not starting (PID lock conflict)**:
```bash
# Remove stale PID lock if the previous process crashed
rm -f data/telegram-kb-agent/.bot.pid
python3 skills/telegram-kb-agent/scripts/bot_daemon.py
```

## What NOT to Change Without Reading DECISIONS.md

- The PID lock mechanism — removing it risks Long Polling conflicts that break Telegram
- The `top_k=5` retrieval limit — calibrated for `gemma3:12b`'s context window with RAG passages
- The HITL `/hitl approve` command handler — it's the only recovery mechanism for paused pipelines
- ChromaDB collection name — changing it without re-indexing breaks all queries
