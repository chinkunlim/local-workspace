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

# Telegram Knowledge Base Agent (行動知識庫檢索)

**Open Claw Skill**

## 角色與定位
Telegram Knowledge Base Agent 是你知識庫的對外橋樑。它將 `data/wiki/` 內的筆記建立為 ChromaDB 向量庫，並提供 Telegram 聊天機器人介面，讓你隨時可以透過對話進行 RAG (Retrieval-Augmented Generation) 知識檢索。

## 架構說明
本技能包含兩個核心組件：
1. **Indexer (`scripts/indexer.py`)**：掃描 `data/wiki/`，透過 LLM Embedding API 建立 ChromaDB 向量庫。
2. **Bot Daemon (`scripts/bot_daemon.py`)**：長駐執行的 Telegram Bot 服務，負責接收訊息並透過 RAG 檢索知識庫來回答問題。

## 執行方式
### 建立或更新向量庫
```bash
python scripts/indexer.py
```

### 啟動聊天機器人
```bash
python scripts/bot_daemon.py
```

## 全域標準化

- **全域標準化介面 (Global Standardization)**: 採用統一的 CLI 狀態與 DAG 追蹤面板，支援 macOS 原生系統通知 (osascript)，並具備 `KeyboardInterrupt` 優雅中斷保護。
