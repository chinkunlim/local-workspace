---
name: telegram-kb-agent
description: "Telegram Knowledge Base Agent. RAG-based query system using ChromaDB to answer questions via Telegram."
metadata:
  {
    "openclaw":
      {
        "emoji": "📱"
      }
  }
---

# Telegram Knowledge Base Agent

**Open Claw Skill**

## Role & Purpose

The Telegram KB Agent is the external-facing interface to your knowledge base. It indexes all notes in `data/wiki/` into a ChromaDB vector store, and provides a Telegram chatbot interface for on-the-go RAG (Retrieval-Augmented Generation) knowledge retrieval.

## Architecture

This skill contains two core components:

1. **Indexer (`scripts/indexer.py`)**: Scans `data/wiki/`, generates embeddings via the LLM API, and builds/updates the ChromaDB vector store.
2. **Bot Daemon (`scripts/bot_daemon.py`)**: A long-running Telegram bot service that receives messages and answers questions by querying the ChromaDB vector store.

## Usage

### Build or Update the Vector Store

```bash
python3 skills/telegram-kb-agent/scripts/indexer.py
```

### Start the Chatbot

```bash
python3 skills/telegram-kb-agent/scripts/bot_daemon.py
```

## Global Standards

- **Unified CLI Interface**: Supports the standard DAG status tracking panel and `KeyboardInterrupt` graceful shutdown.
- macOS native notifications (`osascript`) on pipeline completion or error.
- The Telegram Bot Token is managed exclusively by the Open Claw intent engine to prevent Long Polling conflicts.
