---
name: telegram_kb_agent
description: Telegram Knowledge Base Agent. RAG-based query system using ChromaDB
  to answer questions via Telegram.
metadata:
  openclaw:
    emoji: 📱
    display_name: Telegram 知識庫
state_tracking:
  phases:
  - p1_index
  - p2_bot
  labels:
    p1_index: P1 (Index)
    p2_bot: P2 (Bot)
io_contracts:
  consumes:
  - text/markdown
  produces:
  - text/markdown
---

# Telegram Knowledge Base Agent

**Open Claw Skill**

## Role & Purpose

The Telegram KB Agent is the external-facing interface to your knowledge base. It indexes all notes in `data/wiki/` into a ChromaDB vector store, and provides a Telegram chatbot interface for on-the-go RAG (Retrieval-Augmented Generation) knowledge retrieval.

## Architecture

This skill contains two core components:

1. **Indexer (`scripts/indexer.py`)**: Scans `data/wiki/`, generates embeddings via the LLM API, and builds/updates the ChromaDB vector store.
2. **Bot Daemon (`scripts/bot_daemon.py`)**: A long-running Telegram bot service that receives messages and answers questions by querying the ChromaDB vector store.

## Quick Start (Usage)

### Build or Update the Vector Store

```bash
python3 skills/telegram_kb_agent/scripts/indexer.py
```

### Start the Chatbot

```bash
python3 skills/telegram_kb_agent/scripts/bot_daemon.py
```

## Anti-Hallucination & Safety Guardrails

- **Strict RAG Isolation**: Answers are generated strictly from ChromaDB retrieved contexts. The prompt template severely penalizes out-of-domain hallucination.
- **Runtime Model Guard**: Model switching via Telegram is restricted to explicitly whitelisted models in `config.yaml` to prevent injection of malicious model pulls.

## Global Standards

- **Unified CLI Interface**: Supports the standard DAG status tracking panel and `KeyboardInterrupt` graceful shutdown.
- macOS native notifications (`osascript`) on pipeline completion or error.
- The Telegram Bot Token is managed exclusively by the Open Claw intent engine to prevent Long Polling conflicts.
