---
name: knowledge-compiler
description: "Knowledge Base Compiler. Analyzes and links all markdown outputs to generate bidirectional wiki notes."
metadata:
  {
    "openclaw":
      {
        "emoji": "🧠"
      }
  }
---

# Knowledge Compiler (知識庫編譯器)

> **Pipeline**: Scans `doc-parser` and `audio-transcriber` outputs → Links concepts → Generates `data/wiki` Markdown

## Quick Start

```bash
# 互動式編譯
python3 skills/knowledge-compiler/scripts/run_all.py

# 背景批次編譯 (Headless Batch Mode)
python3 skills/knowledge-compiler/scripts/run_all.py --process-all

# 強制重跑
python3 skills/knowledge-compiler/scripts/run_all.py --force
```

## 核心防護 (V2.0 Antigravity)

- **絕對零度 (Zero Temperature)**: 預設 `config/config.yaml` 強制設定 `temperature: 0`，以確保知識庫合成過程具備 100% 的決定性，徹底消除 LLM 幻覺與語意偏移。
- **無縫 CLI**: 支援統一的 `--process-all` 與 `--log-json` 以相容 Headless 基礎設施。

## 全域標準化

- **全域標準化介面 (Global Standardization)**: 採用統一的 CLI 狀態與 DAG 追蹤面板 (`📊 知識庫編譯狀態與 DAG 追蹤面板`)，支援 macOS 原生系統通知 (osascript)，並具備 `KeyboardInterrupt` 優雅中斷保護。
