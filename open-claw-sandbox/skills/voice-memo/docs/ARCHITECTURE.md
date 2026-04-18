# Open Claw — Voice Memo Skill Architecture

> Version: V8.0 | Last Updated: 2026-04-19

## 1. 概覽

Voice Memo Skill 是 Open Claw 的語音轉錄知識化流水線，負責將 `.m4a` 語音備忘錄逐步轉化為結構化的 Notion 知識文件。

```
01_raw_data/<subject>/lecture.m4a
          │
          ▼ P1: Whisper / MLX 轉錄
01_transcript/<subject>/lecture.md
          │
          ▼ P2: LLM 校對 + 術語保護
02_proofread/<subject>/lecture.md
          │
          ▼ P3: 跨段合併精煉
03_merged/<subject>/lecture.md
          │
          ▼ P4: 重點標記 (Delegates to smart-highlighter)
04_highlighted/<subject>/lecture.md
          │
          ▼ P5: Notion 知識合成 (Delegates to note-generator)
05_notion_synthesis/<subject>/lecture.md
```

---

## 2. 目錄結構

```
skills/voice-memo/
├── SKILL.md                    # Quick-start 指南
├── config/
│   ├── config.yaml             # 所有模型、路徑、閾值設定
│   └── prompt.md               # Phase 2–5 LLM 指令模板
├── docs/
│   ├── ARCHITECTURE.md         # 本文件
│   ├── DECISIONS.md            # 技術決策日誌
│   └── CLAUDE.md               # AI 協作上下文
└── scripts/
    ├── run_all.py              # Orchestrator — 互動式五階段執行器
    ├── phases/
    │   ├── p00_glossary.py     # Phase 0: 術語表初始化
    │   ├── p01_transcribe.py   # Phase 1: 音頻轉錄 (Whisper/MLX)
    │   ├── p02_proofread.py    # Phase 2: LLM 智能校對
    │   ├── p03_merge.py        # Phase 3: 跨段合併精煉
    │   ├── p04_highlight.py    # Phase 4: 重點標記
    │   └── p05_synthesis.py    # Phase 5: Notion 合成輸出
    └── utils/
        └── subject_manager.py  # 語音特有 CLI 互動 (reprocess prompts)
```

---

## 3. 核心架構原則

### 3.1 繼承關係

每個 Phase 類別繼承自 `core.PipelineBase`：

```python
class Phase2Proofread(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p2", phase_name="智能校對")
        # self.dirs["p2"] → data/voice-memo/output/02_proofread  (從 config.yaml 讀取)
        # self.llm       → OllamaClient (自動配置)
        # self.state_manager → StateManager (自動配置)
```

### 3.2 路徑解析 (Config-Driven)

所有路徑從 `config.yaml` 的 `paths:` section 讀取，無任何 hardcode：

```yaml
# skills/voice-memo/config/config.yaml
paths:
  input:  "input/raw_data"
  output: "output"
  state:  "state"
  logs:   "logs"
  phases:
    p0: "input/raw_data"
    p1: "output/01_transcript"
    p2: "output/02_proofread"
    p3: "output/03_merged"
    p4: "output/04_highlighted"
    p5: "output/05_notion_synthesis"
```

### 3.3 狀態追蹤

- `core.StateManager` 管理 `data/voice-memo/state/.pipeline_state.json`
- 每個 Phase 完成後自動寫入 ✅ 符號
- 手動修改輸出 `.md` 檔案時，SHA-256 異常會觸發 DAG Cascade 重置
- `data/voice-memo/state/checklist.md` 是自動生成的人類可讀進度表

### 3.4 中斷恢復 (Checkpoint Resume)

- `run_all.py` 支援 `Ctrl+C` 優雅停機（第一次）和強制停機（第二次）
- 透過 `core.StateManager.save_checkpoint()` 記錄暫停位置
- `--resume` flag 自動從上次中斷點繼續

---

## 4. 資料流

```
[input/raw_data/subject/]  ──(Watchdog)──►  [InboxDaemon]
                                                  │
                                            觸發 run_all.py
                                                  │
                                    ┌─────────────┼─────────────┐
                                   P0            P1             P2
                               (術語表)        (轉錄)         (校對)
                                                  │
                                    ┌─────────────┼─────────────┐
                                   P3            P4             P5
                               (合併)          (標記)         (合成)
                                                  │
                                       [output/05_notion_synthesis/]
```

---

## 5. 與 Core/Skills 的依賴關係

| Core/Skill 模組 | Voice Memo 用途 |
|:---|:---|
| `PipelineBase` | 所有 Phase 類別的基底 |
| `StateManager(skill_name="voice-memo")` | P1-P5 進度追蹤，phases = `["p1"..."p5"]` |
| `PathBuilder` | 從 config.yaml `paths.phases` 解析目錄 |
| `OllamaClient` | P2-P3 LLM 推論 |
| `GlossaryManager` | 術語表同步至 pdf-knowledge |
| `DiffEngine` | P1↔P2 差異檢視（Web UI Review Board）|
| `SystemInboxDaemon` | 監聽 `input/raw_data/` 新增音檔 |
| `SmartHighlighter` | P4 核心標記引擎 (standalone skill) |
| `NoteGenerator` | P5 核心合成引擎 (standalone skill) |

---

## 6. 執行方式

```bash
# 進入 skill 目錄執行（推薦）
cd open-claw-sandbox
python3 skills/voice-memo/scripts/run_all.py

# 只執行特定科目
python3 skills/voice-memo/scripts/run_all.py --subject 助人歷程

# 強制重跑（覆寫已完成的輸出）
python3 skills/voice-memo/scripts/run_all.py --force

# 從斷點恢復
python3 skills/voice-memo/scripts/run_all.py --resume

# 切換 LLM 模型設定
python3 core/cli_config_wizard.py --skill voice-memo
```

---

## 7. 設定切換模型

`config.yaml` 使用 `active_profile` 機制：

```yaml
phase2:
  active_profile: strict_gemma
  profiles:
    strict_gemma:
      model: gemma3:12b
      chunk_size: 3000
    fast_draft:
      model: gemma3:4b
      chunk_size: 5000
```

呼叫 `python3 core/cli_config_wizard.py --skill voice-memo` 可互動式切換。
