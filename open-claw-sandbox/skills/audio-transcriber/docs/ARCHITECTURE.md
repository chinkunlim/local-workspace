# Open Claw — Audio Transcriber Skill Architecture

> Version: V8.1 | Last Updated: 2026-04-20

## 1. 概覽

Audio Transcriber Skill 是 Open Claw 的語音轉錄知識化流水線，負責將 `.m4a` 語音備忘錄逐步轉化為結構化的 Notion 知識文件。

```
01_raw_data/<subject>/lecture.m4a
          │
          ▼ P1: Whisper / MLX 轉錄 (V8.1 三層抗幻覺防禦)
            ├─ Layer 0: Native API 防禦 (condition_on_previous_text=False)
            ├─ Layer 1: VAD 前處理 (pydub 靜音切除 + 移除率安全閥)
            ├─ 語言偵測: 多片段多數投票 (可透過 force_language 關閉)
            └─ Layer 2: 局部重試 (N-gram/zlib 重複率偵測)
          │
01_transcript/<subject>/lecture.md
          │
          ▼ P2: LLM 校對 + 術語保護
02_proofread/<subject>/lecture.md
          ▼ P3: 跨段合併精煉
03_merged/<subject>/lecture.md
```

---

## 2. 目錄結構

```
skills/audio-transcriber/
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
    │   └── p03_merge.py        # Phase 3: 跨段合併精煉
    └── utils/
        └── subject_manager.py  # 語音特有 CLI 互動 (reprocess prompts)
```

---

## 3. 核心架構原則與抗幻覺機制 (V8.1)

### 3.0 三層抗幻覺防禦 (Triple-Layer Anti-Hallucination Defense)

針對 Whisper 在高噪音/長靜音環境下容易產生的「無限重複迴圈 (Hallucination Loop)」，Phase 1 導入了三層防禦：

1. **Layer 0 (原生層)**: 啟用 `condition_on_previous_text=False` 與 `hallucination_silence_threshold` 等 MLX/Whisper 內建防禦參數。
2. **Layer 1 (輸入層 - VAD)**: 使用 `pydub.silence` 在轉錄前切除靜音。設有 `vad_max_removal_ratio` (預設 90%) 作為安全閥，若切除過多將 Fallback 回原始音檔。
3. **Layer 2 (後處理層 - 重複偵測)**: 使用 N-gram 與 zlib 壓縮率掃描生成的 Segments。若偵測到重複幻覺，自動以較高的 Temperature 針對該 Segment 執行局部重試 (`retry_segment`)。
4. **語言偵測**: 採取「前中後 3 片段多數決投票」，避免單一片段靜音導致語言誤判（可於 `config.yaml` 透過 `force_language` 覆寫以加速）。

---

### 3.1 繼承關係

每個 Phase 類別繼承自 `core.PipelineBase`：

```python
class Phase2Proofread(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p2", phase_name="智能校對")
        # self.dirs["p2"] → data/audio-transcriber/output/02_proofread  (從 config.yaml 讀取)
        # self.llm       → OllamaClient (自動配置)
        # self.state_manager → StateManager (自動配置)
```

### 3.2 路徑解析 (Config-Driven)

所有路徑從 `config.yaml` 的 `paths:` section 讀取，無任何 hardcode：

```yaml
# skills/audio-transcriber/config/config.yaml
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
```

### 3.3 狀態追蹤

- `core.StateManager` 管理 `data/audio-transcriber/state/.pipeline_state.json`
- 每個 Phase 完成後自動寫入 ✅ 符號
- 手動修改輸出 `.md` 檔案時，SHA-256 異常會觸發 DAG Cascade 重置
- `data/audio-transcriber/state/checklist.md` 是自動生成的人類可讀進度表

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
                                                  P3
                                                (合併)
                                                  │
                                        [output/03_merged/]
```

---

## 5. 與 Core/Skills 的依賴關係

| Core/Skill 模組 | Audio Transcriber 用途 |
|:---|:---|
| `PipelineBase` | 所有 Phase 類別的基底 |
| `StateManager(skill_name="audio-transcriber")` | P1-P3 進度追蹤，phases = `["p1"..."p3"]` |
| `PathBuilder` | 從 config.yaml `paths.phases` 解析目錄 |
| `OllamaClient` | P2-P3 LLM 推論 |
| `GlossaryManager` | 術語表同步至 doc-parser |
| `DiffEngine` | P1↔P2 差異檢視（Web UI Review Board）|
| `SystemInboxDaemon` | 監聽 `input/raw_data/` 新增音檔 |

---

## 6. 執行方式

```bash
# 進入 skill 目錄執行（推薦）
cd open-claw-sandbox
python3 skills/audio-transcriber/scripts/run_all.py

# 只執行特定科目
python3 skills/audio-transcriber/scripts/run_all.py --subject 助人歷程

# 強制重跑（覆寫已完成的輸出）
python3 skills/audio-transcriber/scripts/run_all.py --force

# 從斷點恢復
python3 skills/audio-transcriber/scripts/run_all.py --resume

# 切換 LLM 模型設定
python3 core/cli_config_wizard.py --skill audio-transcriber
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

呼叫 `python3 core/cli_config_wizard.py --skill audio-transcriber` 可互動式切換。
