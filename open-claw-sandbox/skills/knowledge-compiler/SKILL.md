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

## 全域標準化 (Omega Integration)

- **統一 CLI 介面**: 所有啟動腳本皆具備三大標準機制：
  1. **啟動前置檢查 (Preflight Check)**：驗證依賴與配置無誤。
  2. **狀態與 DAG 追蹤面板 (Dashboard)**：即時視覺化顯示管線進度。
  3. **互動選取與重跑機制 (Interactive Menu)**：可動態選擇 PENDING 或 COMPLETED 任務。
- 支援 macOS 原生系統通知 (osascript)，並具備 `KeyboardInterrupt` 優雅中斷與斷點保存功能。
