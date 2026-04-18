# Open Claw Skills

> Skills are modular, self-contained AI processing pipelines that share the `core/` framework.

## Available Skills

| Skill | 輸入 | 輸出 | 狀態 |
|:---|:---|:---|:---:|
| [voice-memo](voice-memo/SKILL.md) | `.m4a` 語音錄音 | Notion-ready `.md` 知識文件 | ✅ Production |
| [pdf-knowledge](pdf-knowledge/SKILL.md) | `.pdf` 學術/技術文件 | 結構化 Markdown 知識庫 | ✅ Production |

## Skill 通用結構

每個 skill 遵循以下標準目錄結構：

```
skills/<skill-name>/
├── SKILL.md              # Quick-start 指南（必要）
├── config/
│   └── config.yaml       # 路徑、模型、閾值（必要）
├── docs/
│   ├── ARCHITECTURE.md   # 技術架構文件
│   ├── DECISIONS.md      # 技術決策日誌
│   └── CLAUDE.md         # AI 協作上下文
└── scripts/
    ├── run_all.py         # 入口點 Orchestrator
    └── phases/
        └── p<nn>_<name>.py  # Phase 腳本（p01_, p02_ 格式）
```

## 建立新 Skill 的步驟

### 1. 建立目錄

```bash
mkdir -p skills/my-skill/{config,docs,scripts/phases}
```

### 2. 設定 `config/config.yaml`

```yaml
paths:
  input:  "input/my_inbox"
  output: "output"
  state:  "state"
  logs:   "logs"
  phases:
    phase1: "output/01_result"
    phase2: "output/02_final"

runtime:
  ollama:
    api_url: "http://localhost:11434/api/generate"
    timeout_seconds: 600
```

### 3. 建立 Phase 腳本

```python
# scripts/phases/p01_process.py
from core.bootstrap import ensure_core_path
ensure_core_path(__file__)

from core import PipelineBase

class Phase1Process(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="p1",
            phase_name="我的處理",
            skill_name="my-skill"
        )
        # self.dirs["phase1"] 自動從 config.yaml 解析
```

### 4. 建立 `run_all.py`

繼承 `PipelineBase`，在 `startup_check()` 後呼叫 `self.state_manager.sync_physical_files()` 初始化進度追蹤。

### 5. 更新 `inbox_daemon.py`

在 `core/inbox_daemon.py` 的 skill 設定中加入新 skill 的 Inbox 監聽路徑。

## 全域規範

- 所有 Phase 腳本第一行：`from core.bootstrap import ensure_core_path; ensure_core_path(__file__)`
- 所有路徑透過 `self.dirs[key]` 存取，不得 hardcode
- 輸出必須使用 `core.AtomicWriter` 寫入，避免寫入中斷留下破損檔案
- 每個 Phase 完成後呼叫 `self.state_manager.update_task(subject, filename, phase_key, "✅")`
