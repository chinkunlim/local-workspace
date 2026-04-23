---
name: audio-transcriber
description: End-to-end voice processing pipeline. Converts .m4a audio into polished, MLX-Whisper transcribed Notion-ready study material.
metadata:
  {
    "openclaw":
      {
        "emoji": "🎙️"
      }
  }
---

# Audio Transcriber Skill

> **Pipeline**: M4A → Transcript → Proofread → Merge

## Quick Start

```bash
# 1. 放音檔進 Inbox（Universal Drop Zone）
cp lecture.m4a data/raw/助人歷程/

# 2. 執行流水線 (Headless Batch Mode)
python3 skills/audio-transcriber/scripts/run_all.py --process-all

# 3. 查看進度
cat data/audio-transcriber/state/checklist.md
```

## 核心防禦機制 (V8.1 Anti-Hallucination)

| Phase | 腳本 | 功能 |
|:---:|:---|:---|
| P0 | `p00_glossary.py` | 術語表初始化，防止 LLM 生造詞 |
| P1 | `p01_transcribe.py` | 高精度轉錄。**VAD 靜音切除防護網**：使用 `pydub.silence` 預先切除雜音。若 `silence_ratio > max_removal_ratio`（預設 0.90）則自動 Fallback 至原始音檔，防止過度切除導致斷句。包含多片段多數決語言偵測。 |
| P2 | `p02_proofread.py` | LLM 智能校對 + 術語保護 |
| P3 | `p03_merge.py` | 跨段合併精煉 |

## 常用指令

```bash
# 只處理特定科目
python3 skills/audio-transcriber/scripts/run_all.py --subject 助人歷程

# 從斷點恢復
python3 skills/audio-transcriber/scripts/run_all.py --resume

# 背景批次執行 (自動處理全部)
python3 skills/audio-transcriber/scripts/run_all.py --process-all

# 輸出 JSON 格式日誌 (Headless Telemetry)
python3 skills/audio-transcriber/scripts/run_all.py --process-all --log-json

# 強制重跑（覆寫已完成）
python3 skills/audio-transcriber/scripts/run_all.py --force --subject 助人歷程

# 互動切換模型
python3 core/cli_config_wizard.py --skill audio-transcriber
```

## 設定檔位置

- **主設定**: `config/config.yaml` — 模型選擇、路徑、閾值
- **LLM 指令**: `config/prompt.md` — Phase 2–3 的 System Prompt
- **詳細文件**: `docs/ARCHITECTURE.md`

## 全域標準化

- **全域標準化介面 (Global Standardization)**: 採用統一的 CLI 狀態與 DAG 追蹤面板 (`📊 語音轉錄狀態與 DAG 追蹤面板`)，支援 macOS 原生系統通知 (osascript)，並具備 `KeyboardInterrupt` 優雅中斷保護。
