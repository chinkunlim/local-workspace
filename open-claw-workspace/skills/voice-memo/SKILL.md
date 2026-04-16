# Voice Memo Skill

> **Pipeline**: M4A → Transcript → Proofread → Merge → Highlight → Notion MD

## Quick Start

```bash
# 1. 放音檔進 Inbox（按科目分類）
cp lecture.m4a data/voice-memo/input/raw_data/助人歷程/

# 2. 執行流水線
python3 skills/voice-memo/scripts/run_all.py

# 3. 查看進度
cat data/voice-memo/state/checklist.md

# 4. Review Board（差異比對，瀏覽器）
open http://localhost:5001
```

## 五個 Phase

| Phase | 腳本 | 功能 |
|:---:|:---|:---|
| P0 | `p00_glossary.py` | 術語表初始化，防止 LLM 生造詞 |
| P1 | `p01_transcribe.py` | MLX-Whisper 高精度轉錄 |
| P2 | `p02_proofread.py` | LLM 智能校對 + 術語保護 |
| P3 | `p03_merge.py` | 跨段合併精煉 |
| P4 | `p04_highlight.py` | 重點概念標記 |
| P5 | `p05_synthesis.py` | Notion-ready 知識合成 |

## 常用指令

```bash
# 只處理特定科目
python3 skills/voice-memo/scripts/run_all.py --subject 助人歷程

# 從斷點恢復
python3 skills/voice-memo/scripts/run_all.py --resume

# 強制重跑（覆寫已完成）
python3 skills/voice-memo/scripts/run_all.py --force

# 互動切換模型
python3 core/cli_config_wizard.py --skill voice-memo
```

## 設定檔位置

- **主設定**: `config/config.yaml` — 模型選擇、路徑、閾值
- **LLM 指令**: `config/prompt.md` — Phase 2–5 的 System Prompt
- **詳細文件**: `docs/ARCHITECTURE.md`
