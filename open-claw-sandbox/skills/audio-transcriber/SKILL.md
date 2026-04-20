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
# 1. 放音檔進 Inbox（按科目分類）
cp lecture.m4a data/audio-transcriber/input/raw_data/助人歷程/

# 2. 執行流水線
python3 skills/audio-transcriber/scripts/run_all.py

# 3. 查看進度
cat data/audio-transcriber/state/checklist.md

# 4. Review Board（差異比對，瀏覽器）
open http://localhost:5001
```

## 三個 Phase

| Phase | 腳本 | 功能 |
|:---:|:---|:---|
| P0 | `p00_glossary.py` | 術語表初始化，防止 LLM 生造詞 |
| P1 | `p01_transcribe.py` | MLX-Whisper 高精度轉錄 (內建三層抗幻覺防禦、VAD 與多片段語言偵測) |
| P2 | `p02_proofread.py` | LLM 智能校對 + 術語保護 |
| P3 | `p03_merge.py` | 跨段合併精煉 |

## 常用指令

```bash
# 只處理特定科目
python3 skills/audio-transcriber/scripts/run_all.py --subject 助人歷程

# 從斷點恢復
python3 skills/audio-transcriber/scripts/run_all.py --resume

# 強制重跑（覆寫已完成）
python3 skills/audio-transcriber/scripts/run_all.py --force

# 互動切換模型
python3 core/cli_config_wizard.py --skill audio-transcriber
```

## 設定檔位置

- **主設定**: `config/config.yaml` — 模型選擇、路徑、閾值
- **LLM 指令**: `config/prompt.md` — Phase 2–3 的 System Prompt
- **詳細文件**: `docs/ARCHITECTURE.md`
