# 🤖 Complete AI Ecosystem Master Guide — Version 9

> **MacBook Pro M5 · 16GB RAM · Local + Cloud Hybrid**  
> Updated: April 2026 — Reflects current production architecture

---

## 🚀 NEW: Architectural Paradigm (V2 Antigravity Checkpoint)

The Open Claw ecosystem has evolved from a monolithic Flask-bound application to a robust, headless asynchronous architecture designed for 24/7 continuous operation. As part of the **Google Antigravity** architectural evolution, the entire repository was migrated from the legacy `open-claw-workspace` nomenclature to the unified `local-workspace` implementation, structurally decoupling the Core engine from its Sandbox experimentation layers.

### Headless Dual-Engine Orchestration
- **`SystemInboxDaemon`**: A highly resilient, watchdog-driven background process. It monitors multiple `/input/` drop-zones utilizing atomic debouncing and strict lockfiles (`run_pipelines.lock`) to prevent race conditions during rapid I/O events.
- **`BotDaemon`**: A Telegram-based command-and-control interface. It facilitates asynchronous dispatching (`/run`, `/pause`) and status telemetry (`/status`), entirely decoupling the user interface from the heavy processing logic.

### Pipeline Decoupling (Strict Separation of Concerns)
- **Extraction Skills** (`audio-transcriber`, `doc-parser`): Responsible solely for converting raw unstructured data (.m4a, .pdf) into structured, **immutable** Markdown intermediate representations.
- **Synthesis Skills** (`note-generator`, `smart-highlighter`): Operate on the immutable outputs to generate context-aware knowledge artifacts (e.g., Literature Matrices, Anki cards).

### RAM Safety Guard & OOM Defense
Given the severe VRAM/RAM constraints of running local LLMs alongside heavy extraction engines, Open Claw implements a multi-tiered defense:
- **Dead Letter Queue (DLQ)**: The `LocalTaskQueue` forces strictly sequential processing. Tasks exceeding `max_retries=3` are relocated to quarantine.
- **Explicit Model Lifecycle Management**: Every Phase that initializes an Ollama model must wrap execution in a `try...finally` block that explicitly calls `self.llm.unload_model()`. `mx.clear_cache()` is invoked manually.
- **Strict Temperature Control**: Data extraction and reasoning tasks are hardcoded to `temperature: 0` to enforce deterministic outputs and eliminate hallucination drift.

---

## 📋 What Changed in Version 9 (This Document)

| Section                            | Change                                                                                      |
| ---------------------------------- | ------------------------------------------------------------------------------------------- |
| **open-claw-sandbox 架構**       | ✅ **UPDATED** — 完整重構：新增 `core/` 共享框架、`skills/` 技能目錄、`data/` 運行時資料分離 |
| **Voice-Memo Pipeline (Part 11)**  | ✅ **UPDATED** — V3.6.1 → 現行版本：6 個 Phase (P0–P5)，MLX-Whisper，非 Docker 執行          |
| **PDF Knowledge Skill (Part 11b)** | ✅ **ADDED** — 全新技能：7 個 Phase，Docling 深度提取 + VLM 圖像分析                         |
| **Open Claw Dashboard (Part 10)**  | ✅ **ADDED** — Flask Web UI (port 5001)，含 Review Board 差異比對                            |
| **Inbox Daemon (Part 10)**         | ✅ **ADDED** — 自動監聽 Inbox，有新檔案即觸發流水線                                          |
| **start.sh / stop.sh**             | ✅ **UPDATED** — 現在啟動 7 個服務（含 Dashboard + Inbox Daemon）                            |
| **watchdog.sh**                    | ✅ **UPDATED** — 支援多模型同時卸載 + Speculative pages 計算                                 |
| **系統架構圖**                     | ✅ **UPDATED** — 新增 Open Claw Dashboard 層                                                 |

---

## ✅ Your Confirmed Working Setup

```
Workspace:          ~/Desktop/local-workspace/
Open WebUI:         .../local-workspace/open-webui/        (DATA_DIR)
Pipelines:          .../local-workspace/pipelines/         (git clone repo)
LiteLLM:            .../local-workspace/litellm/           (.venv here)
LiteLLM config:     .../local-workspace/litellm-config.yaml
Watchdog:           .../local-workspace/watchdog.sh        (logs → logs/ram_watchdog.log)
Open Claw API:      openclaw gateway · port 18789
Open Claw Dashboard:.../open-claw-sandbox/core/web_ui/   · port 5001
Open Claw Workspace:.../local-workspace/open-claw-sandbox/
  ├── core/         共享框架（所有 skills 共用）
  ├── skills/
  │   ├── voice-memo/   🎙️ M4A → Notion Markdown（6 Phases）
  │   └── pdf-knowledge/ 📄 PDF → Markdown KB（7 Phases）
  ├── data/         運行時資料（不進 git）
  └── models/       HuggingFace 模型快取
All venvs use uv, not pip. Always activate: source .venv/bin/activate
Python dependencies: pip3 install -r open-claw-sandbox/ops/requirements.txt
```

---

## 🗺️ Phase Roadmap (Implementation Order)

| Phase   | What You Build                                            | Time   | Safe to Skip?         |
| ------- | --------------------------------------------------------- | ------ | --------------------- |
| Phase 1 | Fix Ollama settings + assign the right model for each job | 20 min | No — foundation       |
| Phase 2 | Set up LM Studio with the correct MLX models              | 20 min | No — needed for PDFs  |
| Phase 3 | Connect Open WebUI to all your AI sources                 | 20 min | No — command centre   |
| Phase 4 | LiteLLM — multiply your Gemini quota to 300 req/day       | 15 min | No — cost safety      |
| Phase 5 | Pipelines — RAM Guard + Gemini Cost Guard                 | 20 min | No — crash prevention |
| Phase 6 | MD File System — shared brain for all tools               | 15 min | No — state management |
| Phase 7 | VS Code + Cline + MCP — development superpowers           | 30 min | Can defer             |
| Phase 8 | Open Claw night automation + RAM Watchdog daemon          | 45 min | Can defer             |
| Phase 9 | Voice-memo Pipeline (Whisper + Proofread + Notion)        | 60 min | Can defer             |

> Each phase builds on the previous. Complete them in order.

---

## 🏗️ System Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│  LAYER 6 — SKILLS (open-claw-sandbox)                  │
│  voice-memo (P0–P5) · pdf-knowledge (P0a–P3)             │
│  core/ shared framework · Dashboard :5001                │
│  Inbox Daemon · Review Board (diff UI)                   │
├──────────────────────────────────────────────────────────┤
│  LAYER 5 — AUTOMATION (Open Claw API :18789)             │
│  Skill orchestration · Telegram reporting                │
├──────────────────────────────────────────────────────────┤
│  LAYER 4 — STATE MEMORY (MD File System)                 │
│  AGENTS.md · SOUL.md · USER.md · TOOLS.md               │
│  skills/<skill>/docs/ARCHITECTURE.md · DECISIONS.md     │
├──────────────────────────────────────────────────────────┤
│  LAYER 3 — DEV ENVIRONMENT (VS Code + Cline + MCP)       │
│  GitHub Copilot · Cline · MCP servers                    │
├──────────────────────────────────────────────────────────┤
│  LAYER 2 — ORCHESTRATION (Open WebUI + LiteLLM)          │
│  Pipelines · Filters · LiteLLM → 3 Gemini keys          │
├──────────────────────────────────────────────────────────┤
│  LAYER 1 — COMPUTE (Ollama :11434 + LM Studio :1234)     │
│  qwen2.5-coder:7b · deepseek-r1:14b · gemma3:12b        │
│  MLX Whisper Large v3 · Docling models                   │
└──────────────────────────────────────────────────────────┘
```

**Core Design Principle:** Local first → Cloud only when local genuinely cannot handle the task.

| Layer                        | Role                                                    |
| ---------------------------- | ------------------------------------------------------- |
| Compute (Ollama + LM Studio) | Raw inference — unlimited, private                      |
| Open WebUI                   | Router / Command centre — all models in one UI          |
| LiteLLM                      | API gateway — 3 Gemini accounts as one endpoint         |
| Cline + MCP Servers          | Agentic execution — file system, GitHub, Docker         |
| open-claw-sandbox          | Skill sandbox — voice-memo + pdf-knowledge pipelines    |
| core/ framework              | Shared modules: PipelineBase, StateManager, DiffEngine… |
| Open Claw Dashboard          | Web UI :5001 — status, live logs, Review Board diff     |
| Inbox Daemon                 | Auto-trigger pipelines when new files appear in Inbox   |

---

## PART 1 — Ollama: Complete Setup

> ⚠️ **Modelfiles have been REMOVED from this version.** Direct model names (e.g. `qwen2.5-coder:7b`) are used throughout. Modelfiles added unnecessary complexity with minimal benefit for this setup.

### 1.1 Environment Variables

Set these via `launchctl` so they persist across reboots (official macOS method):

```bash
# Set via launchctl (persists after reboot — official macOS method)
launchctl setenv OLLAMA_NUM_CTX 8192
launchctl setenv OLLAMA_HOST "0.0.0.0:11434"
launchctl setenv OLLAMA_MAX_LOADED_MODELS 1
# OLLAMA_MAX_LOADED_MODELS 1 means only one model in VRAM at a time.
# Open WebUI does NOT "keep" models — it sends API requests.
# When you switch models, Ollama unloads after KEEP_ALIVE expires.
launchctl setenv OLLAMA_KEEP_ALIVE 5m

# Restart Ollama to apply
pkill Ollama && sleep 2 && open -a Ollama

# Verify (check CONTEXT column = 8192, PROCESSOR = 100% GPU)
ollama ps
```

### 1.2 Model Assignments

> ⚠️ **gemma3:12b uses ~8GB RAM.** Run `ollama ps` first and stop any loaded model before loading it. Never load two models at once on 16GB.

| Model              | Use Case                                      | RAM   |
| ------------------ | --------------------------------------------- | ----- |
| `qwen2.5-coder:7b` | Daily coding (Cline default)                  | ~5GB  |
| `deepseek-r1:8b`   | Logic & reasoning (quick tasks)               | ~5GB  |
| `gemma3:12b`       | Chinese text, documents, lecture proofreading | ~8GB  |
| `deepseek-r1:14b`  | Overnight heavy tasks (manual load only)      | ~10GB |
| `qwen3.5:9b`       | Multilingual dialogue                         | ~6GB  |

```bash
# Pull all models (完整指令，確保抓取最新版本)
ollama pull qwen2.5-coder:7b
ollama pull deepseek-r1:8b
ollama pull gemma3:12b
ollama pull deepseek-r1:14b
ollama pull qwen3.5:9b

# 如果需要下載特定量化版本 (GGUF)，請手動透過 huggingface-cli 下載並建立 Modelfile
# 例如: huggingface-cli download unsloth/DeepSeek-R1-GGUF --include "*Q4_K_M.gguf"
```

# Verify
ollama list
```

> 💡 **Night Mode (manual):** When starting overnight work, manually run:
> `ollama stop qwen2.5-coder:7b && ollama run deepseek-r1:14b warmup`  
> In the morning, reverse it. No crontab needed — this is simpler and safer.

---

## PART 2 — LM Studio v0.4.8: Real Settings

> **🔧 Flash Attention and Threads are HIDDEN for MLX models.**  
> Flash Attention: automatically enabled at the MLX engine level.  
> Threads: macOS scheduler handles automatically for MLX.  
> This only applies to MLX models. GGUF models still show these settings.

### 2.1 Enable Developer Mode

Open LM Studio → gear icon (Settings) → Find `Developer Mode` → toggle ON → Restart LM Studio.

Developer Mode unlocks: Local Server, advanced inference settings, and the per-model configuration gear.

### 2.2 Temperature Location in v0.4.8

After loading a model in the AI Chat tab:
1. Look at the **RIGHT-HAND SIDEBAR**
2. Scroll down to `Inference Parameters` section
3. Temperature slider is there — set to `0.3` for coding tasks, `0.6` for conversation

Alternatively: My Models tab → gear ⚙️ icon → set default parameters that persist across loads.

### 2.3 Settings for Each MLX Model

#### Qwen2.5-Coder-7B MLX — Daily coding server

| Setting                 | Value                   | Notes                                  |
| ----------------------- | ----------------------- | -------------------------------------- |
| Context Length          | 8192                    | Safe for 16GB                          |
| Temperature             | 0.3                     | Low = deterministic, reliable code     |
| GPU Offload             | 100%                    | MLX always uses full GPU — automatic   |
| Flash Attention         | NOT VISIBLE — automatic | MLX handles natively                   |
| Threads                 | NOT VISIBLE — automatic | macOS scheduler manages                |
| Context Overflow Policy | Rolling Window          | Keeps recent context for long sessions |

Start as Local Server: left sidebar server icon → select this model → Start Server → confirm: `Server running at http://localhost:1234`

#### Phi-4-mini-instruct MLX — Document & notes processor

| Setting                 | Value              | Notes                                          |
| ----------------------- | ------------------ | ---------------------------------------------- |
| Context Length          | 32768              | Phi-4-mini supports 128K; 32K is safe for 16GB |
| Temperature             | 0.4                | Balance between accuracy and natural language  |
| KV Cache Quantization   | 4-bit (if visible) | Saves RAM for long contexts                    |
| Context Overflow Policy | Rolling Window     | Essential for long document processing         |

#### Phi-4-reasoning-plus MLX (7.7GB) — Deep analysis

> ⚠️ Close Chrome and check RAM before loading. At 7.7GB, this model + macOS (~4GB) + VS Code (~1GB) ≈ 13GB. Run `ollama ps` to confirm no Ollama model is loaded.

| Setting                 | Value              | Notes                              |
| ----------------------- | ------------------ | ---------------------------------- |
| Context Length          | 8192               | Maximum safe for 16GB              |
| Temperature             | 0.3                | For complex reasoning and analysis |
| KV Cache Quantization   | 4-bit (if visible) | IMPORTANT: saves ~30% RAM          |
| Context Overflow Policy | Rolling Window     | Essential at this model size       |

#### Qwen2.5-Coder-14B MLX (8.6GB) — Complex coding

> 🔴 Only use when 7B genuinely cannot handle the task. Close Docker, Chrome, VS Code extensions before loading.

| Setting               | Value              | Notes                                   |
| --------------------- | ------------------ | --------------------------------------- |
| Context Length        | 4096               | Reduce to fit in 16GB — do NOT use 8192 |
| Temperature           | 0.3                | Coding tasks need consistency           |
| KV Cache Quantization | 4-bit (if visible) | REQUIRED — enable to fit in 16GB        |

#### Nomic-embed-text-v1.5 (GGUF — tiny)

This is a GGUF model. Flash Attention and Threads DO appear for GGUF. Set: Flash Attention ON, Threads 6 (M5 performance core count). This is Open WebUI's RAG embedding model — load when using document search features.

### 2.4 Verify LM Studio Server

```bash
# After clicking 'Start Server' in LM Studio:
curl http://localhost:1234/v1/models

# If you see this error in Open WebUI logs:
# ERROR: Connection error: Cannot connect to host localhost:1234
# → LM Studio Local Server is NOT running
# → Open LM Studio → Local Server → click Start Server
```

---

## PART 3 — Open WebUI: Install & Connect

### 3.1 Install and Start

```bash
# ==========================================
# 方案 A：使用 uvx 直接啟動 (推薦給 macOS 本地環境)
# ==========================================
# Install uv first (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
# Then close and reopen Terminal to refresh PATH

# YOUR working command (confirmed from terminal):
DATA_DIR=/Users/limchinkun/Desktop/local-workspace/open-webui \
  uvx --python 3.11 open-webui@latest serve

# If you get 'ddgs' dependency error, use this instead:
DATA_DIR=/Users/limchinkun/Desktop/local-workspace/open-webui \
  uvx --python 3.11 --with 'ddgs>=9.11.3' open-webui@latest serve

# Open WebUI runs on http://localhost:8080

# ==========================================
# 方案 B：使用 Docker 部署 (若需容器化環境)
# ==========================================
# 必須使用 --network host (Linux) 或正確映射 port 確保能連線至 localhost 的 Ollama
# docker run -d -p 8080:8080 --add-host=host.docker.internal:host-gateway \
#   -v /Users/limchinkun/Desktop/local-workspace/open-webui:/app/backend/data \
#   --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

> ⚠️ **First account = Admin.** Create your account immediately when the page loads.

### 3.2 Connect All AI Sources

Open `http://localhost:8080` → profile icon → Settings → Connections → add:

| Connection               | Type              | URL                        | API Key       |
| ------------------------ | ----------------- | -------------------------- | ------------- |
| Ollama                   | Ollama            | `http://localhost:11434`   | (leave blank) |
| LM Studio                | OpenAI Compatible | `http://localhost:1234/v1` | `lm-studio`   |
| LiteLLM (Gemini gateway) | OpenAI Compatible | `http://localhost:4000/v1` | `dummy`       |
| Pipelines                | OpenAI Compatible | `http://localhost:9099`    | `0p3n-w3bu!`  |

> ℹ️ If LM Studio server is not running, Open WebUI logs `Cannot connect to localhost:1234`. This is harmless. Start LM Studio server when needed, and Open WebUI auto-reconnects.

---

## PART 4 — Pipelines: Install & Configure

> **🔧 Why PyPI packages don't work:**  
> `pipelines` (PyPI) → Python 2 package from 2016  
> `open-webui-pipelines` (PyPI) → broken, no pyproject.toml  
> **CORRECT METHOD: `git clone` then `requirements.txt`**

### 4.1 Install Pipelines

```bash
cd /Users/limchinkun/Desktop/local-workspace

# Clone the official repository
git clone https://github.com/open-webui/pipelines.git
cd pipelines

# Create Python 3.11 virtual environment with uv
uv venv --python 3.11
source .venv/bin/activate

# Install ALL requirements (correct method — not 'open-webui-pipelines')
uv pip install -r requirements.txt

# Install psutil separately (required for RAM Safety Guard)
uv pip install psutil

# Note: this warning is harmless:
# warning: The package google-cloud-aiplatform==1.71.1 does not have an extra named 'all'
```

### 4.2 Start Pipelines Server

> **🔗 infra/scripts/ 聯動機制**：在日常操作中，你不應該手動啟動 Pipeline。請一律使用 `infra/scripts/start.sh`，它會自動為 Pipeline 與所有基礎設施建立正確的背景執行緒與日誌綁定。

手動測試指令如下：
```bash
cd /Users/limchinkun/Desktop/local-workspace/pipelines
source .venv/bin/activate
sh start.sh

# Expected output:
# INFO: Application startup complete.
# INFO: Uvicorn running on http://0.0.0.0:9099
```

### 4.3 Troubleshooting: "No Valves to Update" Error

> 🔴 **Root causes and fixes:**
> 1. Main class MUST be named `class Pipeline:` (NOT `class Filter:`)
> 2. Type hint is CRITICAL: `self.valves: self.Valves = self.Valves()`  
>    Without `: self.Valves` type hint, the scanner ignores the Valves class
> 3. After uploading new code: stop pipelines (Ctrl+C), restart (`sh start.sh`), then in Open WebUI click trash icon on old pipeline and re-upload
> 4. If still failing: `lsof -ti:9099 | xargs kill -9` then restart

### 4.4 RAM Safety Guard — Complete Code

Save as `RAM_Safety_Guard.py`, place in `~/Desktop/local-workspace/pipelines/pipelines/` or upload via Open WebUI → Workspace → Pipelines.

```python
"""
Open WebUI Pipeline: RAM Safety Guard (記憶體安全守衛)
功能：在每次發送對話請求前，自動檢查 Mac 的可用實體記憶體 (RAM)。
如果可用 RAM 低於設定的警戒值，且使用者選擇了重型模型，
系統將自動攔截請求，並強制替換為輕量級的安全模型，防止系統卡死。
環境依賴: uv pip install psutil
"""
import psutil
from typing import Optional
from pydantic import BaseModel, Field

class Pipeline:
    """
    核心管線類別。
    注意：Open WebUI 強制要求主類別必須命名為 'Pipeline'，不可使用 'Filter'。
    """
    class Valves(BaseModel):
        ram_threshold_mb: int = Field(default=4000, description='低記憶體警戒值 (MB)')
        safety_model: str = Field(default='qwen2.5-coder:7b', description='觸發警戒時的輕量替換模型')

    def __init__(self):
        self.valves: self.Valves = self.Valves()
        self.name = 'RAM Safety Guard'

    def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        free_mb = psutil.virtual_memory().available / 1024 / 1024
        model = body.get('model', '').lower()
        HEAVY_KEYWORDS = ['deepseek-v3', 'deepseek-r1', '14b', '32b', '70b',
                          'gemma3:12b', 'phi-4', 'gemma-chinese', 'deepseek-night']
        is_heavy = any(kw in model for kw in HEAVY_KEYWORDS)
        if free_mb < self.valves.ram_threshold_mb and is_heavy:
            body['model'] = self.valves.safety_model
            body['ram_guard_triggered'] = f'Switched: only {free_mb:.0f}MB free'
        return body
```

### 4.5 Gemini Cost Guard — Complete Code

Save as `Gemini_Cost_Guard.py`:

```python
"""
Open WebUI Pipeline: Gemini Cost Guard (API 額度守衛)
功能：自動追蹤並限制每日 Gemini API 的呼叫次數。
當日使用次數達到設定的上限（預設 270 次）時，系統將攔截請求並轉發給本地替換模型。
"""
import json
import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

class Pipeline:
    class Valves(BaseModel):
        daily_limit: int = Field(default=270, description='每日 Gemini API 請求上限')
        safety_buffer: int = Field(default=30, description='保留的安全緩衝次數')
        fallback_model: str = Field(default='qwen2.5-coder:7b', description='額度用盡時的替換模型')
        quota_file_path: str = Field(
            default='/tmp/gemini_quota.json',  # /tmp works in Docker containers
            description='配額追蹤 JSON 檔案路徑'
        )

    def __init__(self):
        self.valves: self.Valves = self.Valves()
        self.name = 'Gemini Cost Guard'

    def _get_quota_data(self) -> dict:
        path = Path(self.valves.quota_file_path)
        today = datetime.date.today().isoformat()
        if not path.exists(): return {'date': today, 'count': 0}
        try:
            data = json.loads(path.read_text())
            if data.get('date') != today: return {'date': today, 'count': 0}
            return data
        except Exception: return {'date': today, 'count': 0}

    def _update_count(self, count: int):
        path = Path(self.valves.quota_file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {'date': datetime.date.today().isoformat(), 'count': count}
        path.write_text(json.dumps(data))

    def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        model_name = body.get('model', '').lower()
        if 'gemini' in model_name:
            quota_data = self._get_quota_data()
            current_count = quota_data['count']
            if current_count >= self.valves.daily_limit:
                body['model'] = self.valves.fallback_model
                body['cost_guard_triggered'] = f'Quota reached ({current_count})'
            else:
                self._update_count(current_count + 1)
        return body
```

### 4.6 Gemini API Free Tier Limits

| Model                        | Daily Limit (RPD)       | Per-Minute (RPM) |
| ---------------------------- | ----------------------- | ---------------- |
| Gemini 1.5 Flash             | 1,500                   | 15               |
| Gemini 1.5 Pro               | 50                      | 2                |
| Gemini 2.5 Pro (via LiteLLM) | ~50 (verify in console) | 2                |

> ℹ️ In the free tier, Google may use your inputs/outputs to train models. For privacy, upgrade to Pay-as-you-go.

### 4.7 Refresh Pipeline After Code Changes

1. Press Ctrl+C in the pipelines terminal to stop
2. Kill orphan processes: `lsof -ti:9099 | xargs kill -9`
3. Run: `sh start.sh`
4. In Open WebUI → Workspace → Pipelines → trash icon on old pipeline → re-upload `.py` file

---

## PART 5 — LiteLLM: Gemini Gateway

> **🔧 Two errors you may encounter:**  
> Error 1: `zsh: command not found: pip` → use `uv pip install` instead  
> Error 2: `ModuleNotFoundError: No module named websockets` → install `litellm[proxy]` not just `litellm`

### 5.1 Install LiteLLM

```bash
cd /Users/limchinkun/Desktop/local-workspace/litellm
uv venv --python 3.11
source .venv/bin/activate

# Install litellm WITH proxy support (fixes: No module named 'websockets')
uv pip install 'litellm[proxy]'
deactivate
```

### 5.2 Create Config File

```bash
cat > /Users/limchinkun/Desktop/local-workspace/litellm-config.yaml << 'EOF'
model_list:
  - model_name: gemini-pro
    litellm_params:
      model: gemini/gemini-2.5-pro
      api_key: "PASTE_ACCOUNT1_KEY_FROM_AISTUDIO_GOOGLE_COM"
  - model_name: gemini-pro
    litellm_params:
      model: gemini/gemini-2.5-pro
      api_key: "PASTE_ACCOUNT2_KEY_FROM_AISTUDIO_GOOGLE_COM"
  - model_name: gemini-pro
    litellm_params:
      model: gemini/gemini-2.5-pro
      api_key: "PASTE_ACCOUNT3_KEY_FROM_AISTUDIO_GOOGLE_COM"
router_settings:
  routing_strategy: least-busy
  retry_after: 60
  allowed_fails: 2
EOF
# Edit to add your real API keys:
nano /Users/limchinkun/Desktop/local-workspace/litellm-config.yaml
```

Get free API keys from: https://aistudio.google.com (one per Google account = 100 req/day each = 300 total/day)

### 5.3 Start LiteLLM

```bash
cd /Users/limchinkun/Desktop/local-workspace/litellm
source .venv/bin/activate
.venv/bin/litellm --config \
  /Users/limchinkun/Desktop/local-workspace/litellm-config.yaml --port 4000

# Expected output:
# LiteLLM: Proxy initialized with Config, Set models: gemini-pro x3
# INFO: Uvicorn running on http://0.0.0.0:4000

# Verify in another terminal tab:
curl http://localhost:4000/health
# Expected: {"status":"healthy"}
```

---

## PART 6 — MCP Servers: VS Code + Cline

### 6.1 Install Node.js

```bash
brew install node
node --version  # should show v22+
npm --version
```

### 6.2 MCP Configuration (.vscode/mcp.json)

Create this file in your project root under `.vscode/mcp.json`:

```json
{
  "servers": {
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "."]
    },
    "github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "YOUR_GITHUB_PAT" }
    },
    "postgres": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-postgres",
               "postgresql://localhost/agri_price_db"]
    },
    "docker": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-docker"]
    },
    "memory": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-memory"]
    },
    "notion": {
      "command": "npx",
      "args": ["@notionhq/notion-mcp-server"],
      "env": { "NOTION_API_KEY": "YOUR_NOTION_KEY" }
    },
    "fetch": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-fetch"]
    },
    "claude-context": {
      "command": "npx",
      "args": ["claude-context-mcp"]
    }
  }
}
```

| MCP Server        | What the Agent Can Do                    | Priority |
| ----------------- | ---------------------------------------- | -------- |
| server-filesystem | Read/write any file in your project      | Critical |
| server-github     | Read/write PRs, issues, commits          | Critical |
| server-postgres   | Query agri-price database                | High     |
| server-docker     | Manage Open Claw sandbox                 | High     |
| server-memory     | Persist key-value memory across sessions | Medium   |
| notion-mcp-server | Archive to Notion databases              | Medium   |
| server-fetch      | Read any URL / documentation page        | Medium   |
| claude-context    | Auto-load entire codebase as context     | High     |

### 6.3 Cline Configuration in VS Code

```
# Install Cline: Cmd+Shift+X → search Cline → install
# Cline Settings (Cmd+Shift+P → 'Cline: Open Settings'):

Provider 1 (Default — 90% of tasks):
  Type: Ollama
  Base URL: http://localhost:11434
  Model: qwen2.5-coder:7b

Provider 2 (Complex tasks / debug — switch manually):
  Type: OpenAI Compatible
  Base URL: http://localhost:4000/v1
  API Key: dummy
  Model: gemini-pro
```

> ℹ️ Store both provider configurations in your `CLAUDE.md` so you can copy-paste during the 10-second switch.

---

## PART 7 — MD File System: Shared Brain

### 7.1 Create File Structure

```bash
mkdir -p ~/projects/agri-price-tracker
mkdir -p ~/projects/thesis-pipeline
mkdir -p ~/papers/psychology ~/papers/audio ~/papers/course-materials
touch ~/.claude_profile.md

for dir in ~/projects/agri-price-tracker ~/projects/thesis-pipeline; do
  cd $dir && touch CLAUDE.md HANDOFF.md TASKS.md PROGRESS.md DECISIONS.md WALKTHROUGH_LOG.md
done

mkdir -p ~/Desktop/local-workspace/project_dev/ai-infrastructure
```

### 7.2 ~/.claude_profile.md Template

```markdown
# My Developer Profile

## Environment
- MacBook Pro M5, 16GB RAM
- Languages: Python 3.12, JavaScript
- Workspace: /Users/limchinkun/Desktop/local-workspace/

## Preferences
- Always explain before writing code
- Functions max 30 lines · 程式碼優先 · 始終提寫測試
- Ask before deleting
- Use Traditional Chinese (繁體中文) for conversations

## Tools
- Cline+qwen2.5-coder:7b: routine coding (daily driver)
- LM Studio Phi-4-mini: PDF/document analysis
- Open Claw: overnight automation (sandbox mandatory)
- Gemini via LiteLLM: complex logic and debugging

## Session Start Protocol
Read ~/.claude_profile.md AND CLAUDE.md. Then read HANDOFF.md and PROGRESS.md.
Tell me the active task and what was last done. Then we begin.

## Session End Protocol
Update HANDOFF.md (exact stopping point) and PROGRESS.md (completed).
If any architectural decision was made, add it to DECISIONS.md.
```

### 7.3 File Usage Reference

| File               | Core Function                                               | Read When                 | Updated When                   | Max Lines        |
| ------------------ | ----------------------------------------------------------- | ------------------------- | ------------------------------ | ---------------- |
| CLAUDE.md          | Project's 'law' — tech stack, code style, conventions       | Every session start       | Stack/conventions change       | 80               |
| HANDOFF.md         | Last session's exact stopping point                         | Every session start       | Overwrite at EVERY session end | 30               |
| TASKS.md           | Task kanban: completed, in progress, blocked                | Every session start       | Task starts/blocks/finishes    | ~50              |
| PROGRESS.md        | Historical log: milestones completed per date               | Every session start       | End of every session           | Archive monthly  |
| DECISIONS.md       | Architecture log: why this library? why not that algorithm? | Before making changes     | Architectural decision made    | Unlimited        |
| WALKTHROUGH_LOG.md | Complex logic walkthroughs designed for Antigravity         | After Antigravity session | After each Antigravity session | Archive 3 months |

### 7.4 Session Start Mantra

> Copy-paste this at the start of every new conversation with Cline or Open WebUI:  
> **"Read ~/.claude_profile.md and CLAUDE.md. Then read HANDOFF.md and PROGRESS.md. Tell me what the current active task is. Then we begin."**

---

## PART 8 — Open Claw: Install + Sandbox + Telegram

> 🔴 **Sandbox is mandatory.** Open Claw executes terminal commands autonomously. The Docker sandbox prevents any accident from touching your personal files. Never skip sandbox setup.

### 8.1 Install Open Claw

```bash
curl -fsSL https://openclaw.ai/install.sh | bash

# If 'openclaw' not found after install:
export PATH="$(npm prefix -g)/bin:$PATH"
echo 'export PATH="$(npm prefix -g)/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

openclaw --version  # confirms: OpenClaw 2026.3.28 or similar
openclaw doctor     # check dependencies
```

### 8.2 Connect Ollama

```bash
openclaw onboard
# Select: Ollama
# URL: http://127.0.0.1:11434  (NO /v1 — breaks tool calling)
openclaw models set ollama/qwen2.5-coder:7b
```

### 8.3 Build Sandbox Image — Manual Download Required

> **🔧 The npm package does NOT bundle the scripts/ folder.** Must manually download all required files from GitHub.

```bash
# 1. Navigate to openclaw installation directory
cd $(npm prefix -g)/lib/node_modules/openclaw

# 2. Download all required files from GitHub
curl -O https://raw.githubusercontent.com/openclaw/openclaw/main/scripts/sandbox-setup.sh
curl -O https://raw.githubusercontent.com/openclaw/openclaw/main/scripts/sandbox-common-setup.sh
curl -O https://raw.githubusercontent.com/openclaw/openclaw/main/Dockerfile.sandbox
curl -O https://raw.githubusercontent.com/openclaw/openclaw/main/Dockerfile.sandbox-common

# 3. Move sandbox-setup.sh into scripts/ subdirectory
mkdir -p scripts && mv sandbox-setup.sh scripts/

# 4. Make scripts executable
chmod +x sandbox-common-setup.sh scripts/sandbox-setup.sh

# 5. Build the sandbox (Docker must be running!)
./sandbox-common-setup.sh
# Expected: builds openclaw-sandbox:bookworm-slim, then openclaw-sandbox-common:bookworm-slim
# Takes 2-5 minutes

# 6. Verify both images exist
docker images | grep openclaw-sandbox
# Should show two rows: openclaw-sandbox-common and openclaw-sandbox
```

### 8.4 Register the Sandbox Image

> ⚠️ After building, you MUST tell Open Claw to use the sandbox image. Without this step, Open Claw ignores the sandbox entirely.

```bash
openclaw config set agents.defaults.sandbox.docker.image \
  "openclaw-sandbox-common:bookworm-slim"

# Restart gateway to apply config
openclaw gateway stop
openclaw gateway start

openclaw doctor
```

### 8.5 Configure Open Claw

Run `openclaw configure` and use Manual mode:

| Setting                 | Value                                                           | Why                             |
| ----------------------- | --------------------------------------------------------------- | ------------------------------- |
| Gateway location        | Local (this machine)                                            | On-campus use                   |
| Gateway bind mode       | Loopback (127.0.0.1)                                            | Security: blocks campus network |
| Tailscale exposure      | Off                                                             | Most secure                     |
| Port                    | 18789                                                           | Default — keep as-is            |
| Generate Token          | Yes                                                             | Security requirement            |
| Provider                | Ollama                                                          | Local model                     |
| URL                     | `http://127.0.0.1:11434`                                        | No /v1 at end!                  |
| Default Model           | `ollama/qwen2.5-coder:7b`                                       | Daily model                     |
| Workspace               | `/Users/limchinkun/Desktop/local-workspace/open-claw-sandbox` | Limit AI file access            |
| Install gateway service | Yes                                                             | Auto-start on boot              |

### 8.6 Full openclaw config JSON

Run `openclaw config edit` and paste (replace `limchinkun` with your username):

```json
{
  "agents": {
    "defaults": {
      "model": { "primary": "ollama/qwen2.5-coder:7b", "fallbacks": ["ollama/deepseek-r1:8b"] },
      "sandbox": {
        "mode": "all", "scope": "session", "workspaceAccess": "rw",
        "docker": {
          "image": "openclaw-sandbox-common:bookworm-slim",
          "binds": [
            "/Users/limchinkun/projects/agri-price-tracker:/workspace/agri:rw",
            "/Users/limchinkun/projects/thesis-pipeline:/workspace/thesis:rw",
            "/Users/limchinkun/papers:/workspace/papers:ro",
            "/Users/limchinkun/papers/audio:/workspace/audio:ro"
          ],
          "network": "none"
        }
      }
    },
    "list": [{ "id": "night",
      "model": { "primary": "ollama/deepseek-r1:14b", "fallbacks": ["ollama/deepseek-r1:8b"] },
      "sandbox": { "mode": "all", "scope": "session", "workspaceAccess": "rw",
        "docker": { "image": "openclaw-sandbox-common:bookworm-slim",
          "binds": [
            "/Users/limchinkun/projects/agri-price-tracker:/workspace/agri:rw",
            "/Users/limchinkun/projects/thesis-pipeline:/workspace/thesis:rw",
            "/Users/limchinkun/papers:/workspace/papers:ro"
          ],
          "network": "none" }}}]
  },
  "models": { "providers": { "ollama": { "apiKey": "ollama-local", "baseUrl": "http://127.0.0.1:11434", "api": "ollama" }}},
  "channels": { "telegram": { "enabled": true, "botToken": "YOUR_BOT_TOKEN",
    "dmPolicy": "allowlist", "allowFrom": ["YOUR_TELEGRAM_USER_ID"] }}
}
```

### 8.7 Telegram Bot Setup

1. Telegram → @BotFather → `/newbot` → save the token
2. Get your Telegram ID: message @userinfobot → it replies with your numeric ID
3. Run: `openclaw channels configure telegram` → enter token → DM Policy: Allowlist → enter your ID

### 8.8 Security Boundaries

| ✅ Open Claw CAN access            | ❌ BLOCKED — Cannot access           |
| --------------------------------- | ----------------------------------- |
| open-claw-sandbox (read+write)  | ~/Documents, ~/Desktop, ~/Downloads |
| Docker sandbox container only     | ~/.ssh (auto-blocked)               |
| /workspace/agri (if configured)   | /etc, /sys, /dev (auto-blocked)     |
| /workspace/thesis (if configured) | Internet (network: none)            |

### 8.9 Uninstall Open Claw — Complete Removal

```bash
# 1. Stop and remove the background service
openclaw daemon uninstall

# 2. Remove Docker sandbox images (frees ~3GB)
docker rmi openclaw-sandbox-common:bookworm-slim
docker rmi openclaw-sandbox:bookworm-slim

# 3. Delete config, tokens, and conversation history
rm -rf ~/.openclaw

# 4. Uninstall the CLI tool
npm uninstall -g openclaw

# 5. Clean ~/.zshrc (remove PATH line if manually added)
nano ~/.zshrc
source ~/.zshrc

# Verify removal:
which openclaw  # Should return: openclaw not found
```

---

## PART 9 — RAM Watchdog Daemon

> ⚠️ **Watchdog script is at `~/Desktop/local-workspace/watchdog.sh`**  
> Logs are written to `local-workspace/logs/ram_watchdog.log` (not `/tmp`)

### 9.1 Watchdog Script (Current Version)

Key improvements over original version:
- RAM calculated as **Free + Inactive + Speculative pages** (matches Activity Monitor)
- Supports **multiple model eviction** in one cycle (loops over all loaded models)
- Uses `ollama stop` CLI first; falls back to API call if CLI is older
- Logs redirected to `local-workspace/logs/` (unified with other services)

```bash
#!/bin/bash
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export WORKSPACE_DIR
export PYTHONPATH="${WORKSPACE_DIR}:${WORKSPACE_DIR}/open-claw-sandbox:${PYTHONPATH}"

LOG_DIR="${WORKSPACE_DIR}/logs"
mkdir -p "$LOG_DIR"
LOG="${LOG_DIR}/ram_watchdog.log"
exec >> "$LOG" 2>&1

CRITICAL_MB=1500
WARNING_MB=2500

trap 'echo "[$(date +'\''%H:%M:%S'\'')] Stopped."; exit 0' SIGINT SIGTERM

log() { echo "[$(date +'%H:%M:%S')] $1"; }

# Free + Inactive + Speculative (matches Activity Monitor)
get_free_mb() {
    vm_stat | awk '
        /Pages free/ {sub(/\./, "", $3); f=$3}
        /Pages inactive/ {sub(/\./, "", $3); i=$3}
        /Pages speculative/ {sub(/\./, "", $3); s=$3}
        END {printf "%.0f\n", (f+i+s)*4096/1048576}'
}

get_models() { ollama ps 2>/dev/null | awk 'NR>1 {print $1}'; }

evict() {
    local model_name="$1" free_ram="$2"
    log "EVICTING $model_name — Only ${free_ram}MB RAM free"
    if ollama stop "$model_name" >/dev/null 2>&1; then
        log "Unloaded $model_name via CLI"
    else
        curl -s -X POST http://localhost:11434/api/generate \
          -d "{\"model\":\"$model_name\",\"keep_alive\":0}" >/dev/null
        log "Unloaded $model_name via API fallback"
    fi
}

log "RAM Watchdog started. DANGER: ${CRITICAL_MB}MB | WARN: ${WARNING_MB}MB"

while true; do
    F=$(get_free_mb)
    if [ "$F" -lt "$CRITICAL_MB" ]; then
        MODELS=$(get_models)
        if [ -n "$MODELS" ]; then
            for M in $MODELS; do evict "$M" "$F"; done
        else
            log "CRITICAL ${F}MB — No Ollama models running. Check Chrome/Other apps!"
        fi
    elif [ "$F" -lt "$WARNING_MB" ]; then
        log "Low RAM Warning: ${F}MB free."
    fi
    sleep 30
done
```

### 9.2 Install as Auto-Start Service

```bash
mkdir -p ~/Library/LaunchAgents
cat > ~/Library/LaunchAgents/com.ai.watchdog.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.ai.watchdog</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string>
    <string>/Users/limchinkun/Desktop/local-workspace/watchdog.sh</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key>
    <string>/Users/limchinkun/Desktop/local-workspace/logs/ram_watchdog.log</string>
  <key>StandardErrorPath</key>
    <string>/Users/limchinkun/Desktop/local-workspace/logs/ram_watchdog.log</string>
</dict></plist>
EOF

launchctl load ~/Library/LaunchAgents/com.ai.watchdog.plist
launchctl list | grep watchdog
tail -f ~/Desktop/local-workspace/logs/ram_watchdog.log
```

---

## PART 10 — Daily Startup & Shutdown Scripts

> The production `start.sh` uses `wait_for_port` (up to 30s per service) instead of fixed `sleep`.  
> It now starts **7 services**. Run from `local-workspace/`:

```bash
bash ~/Desktop/local-workspace/start.sh
```

### 10.1 Services Started by start.sh

| Step | Service                         | Port     | Notes                                                         |
| ---- | ------------------------------- | -------- | ------------------------------------------------------------- |
| 1    | Ollama                          | 11434    | Opens app if not running                                      |
| 2    | LiteLLM                         | 4000     | Gemini gateway; logs → `logs/litellm.log`                     |
| 3    | Open WebUI                      | 8080     | `uvx open-webui@latest serve`; logs → `logs/open-webui.log`   |
| 4    | Pipelines                       | 9099     | `sh start.sh`; logs → `logs/pipelines.log`                    |
| 5    | Open Claw API                   | 18789    | `openclaw gateway`; logs → `logs/openclaw.log`                |
| 6    | **Open Claw Dashboard** *(NEW)* | **5001** | `python3 core/web_ui/app.py`; logs → `logs/dashboard.log`     |
| 7    | **Inbox Daemon** *(NEW)*        | —        | `python3 core/inbox_daemon.py`; PID → `logs/inbox_daemon.pid` |

> The Inbox Daemon auto-triggers voice-memo and pdf-knowledge pipelines when new files appear in their Inbox directories.

### 10.2 Stop Script Key Actions

```bash
bash ~/Desktop/local-workspace/stop.sh
```

Actions performed by `stop.sh`:
1. `openclaw gateway stop`
2. `pkill -f litellm / open-webui / uvx`
3. `lsof -ti:9099 | xargs kill -9` (Pipelines port cleanup)
4. Kill Inbox Daemon via PID file
5. `ollama stop` all loaded models, then `pkill Ollama`
6. Prints current free RAM

### 10.3 All Ports & Services Reference

| Service                 | Port     | Start                                        | Stop                                         |
| ----------------------- | -------- | -------------------------------------------- | -------------------------------------------- |
| Ollama                  | 11434    | Open Ollama app                              | Menu bar → Quit                              |
| LM Studio               | 1234     | Open app → Local Server → Start              | In app → Stop                                |
| LiteLLM (Gemini proxy)  | 4000     | `start.sh`                                   | `stop.sh`                                    |
| Open WebUI              | 8080     | `start.sh`                                   | `stop.sh`                                    |
| Pipelines               | 9099     | `start.sh`                                   | `stop.sh` / `lsof -ti:9099 \| xargs kill -9` |
| Open Claw API           | 18789    | `start.sh`                                   | `openclaw gateway stop`                      |
| **Open Claw Dashboard** | **5001** | `start.sh` or `python3 core/web_ui/app.py`   | `stop.sh`                                    |
| **Inbox Daemon**        | —        | `start.sh` or `python3 core/inbox_daemon.py` | `stop.sh`                                    |

---


```bash
cat > ~/Desktop/local-workspace/start.sh << 'EOF'
#!/bin/bash
echo '=== Starting AI Ecosystem from Local Workspace ==='

# 1. Ollama
if ! pgrep -x 'ollama' > /dev/null; then
  open -a Ollama; sleep 4; echo '✅ Ollama started'
else
  echo '✅ Ollama already running'
fi

# 2. LiteLLM (Gemini gateway)
cd ~/Desktop/local-workspace/litellm
if [ -f '.venv/bin/activate' ]; then
  source .venv/bin/activate
  .venv/bin/litellm --config \
    ~/Desktop/local-workspace/litellm-config.yaml --port 4000 &
  sleep 2; deactivate; echo '✅ LiteLLM :4000 (Gemini Gate)'
fi

# 3. Open WebUI
DATA_DIR=~/Desktop/local-workspace/open-webui \
  uvx --python 3.11 open-webui@latest serve &
sleep 2; echo '✅ Open WebUI :8080'

# 4. Pipelines
cd ~/Desktop/local-workspace/pipelines
if [ -f '.venv/bin/activate' ]; then
  source .venv/bin/activate
  sh start.sh &
  sleep 2; deactivate; echo '✅ Pipelines :9099'
fi

# 5. Open Claw
if ! openclaw gateway status > /dev/null 2>&1; then
  openclaw gateway &; sleep 3; echo '✅ Open Claw :18789'
else
  echo '✅ Open Claw already running'
fi

echo ''
echo '============================================='
echo ' 🌐 Open WebUI → http://localhost:8080'
echo ' 🦞 Open Claw  → http://127.0.0.1:18789'
echo ' 🔷 Gemini Gate → http://localhost:4000'
echo ' 🔌 Pipelines   → http://localhost:9099'
echo ' 🦙 Ollama      → http://localhost:11434'
echo '============================================='
open http://localhost:8080
EOF
chmod +x ~/Desktop/local-workspace/start.sh
```

### 10.2 Stop Script

```bash
cat > ~/Desktop/local-workspace/stop.sh << 'EOF'
#!/bin/bash
echo '=== Stopping AI Ecosystem ==='

# 1. Stop Open Claw
if pgrep -x "node" > /dev/null; then
  openclaw gateway stop
  echo '✅ Open Claw Gateway stopped'
fi

# 2. Stop background Python services
pkill -f "litellm"
pkill -f "open-webui"
pkill -f "uvx"

# 3. Kill orphan Uvicorn/Pipelines on port 9099
lsof -ti:9099 | xargs kill -9 2>/dev/null
echo '✅ Port 9099 (Pipelines) cleared'

# 4. Unload Ollama models
ollama stop $(ollama ps | awk 'NR>1 {print $1}') 2>/dev/null
pkill Ollama
echo '✅ Ollama processes cleared'

echo ''
echo '--- AI Ecosystem Services Stopped ---'
vm_stat | awk '/Pages free/{f=$3}/Pages inactive/{i=$3}END{printf "  Current Free RAM: %.0f MB\n",(f+i)*4096/1048576}'
echo '-------------------------------------'
EOF
chmod +x ~/Desktop/local-workspace/stop.sh
```

### 10.3 All Ports & Services Reference

| Service                | Port  | Start Command                                  | Stop                                      |
| ---------------------- | ----- | ---------------------------------------------- | ----------------------------------------- |
| Ollama (AI engine)     | 11434 | Open Ollama app                                | Ollama menu bar → Quit                    |
| LM Studio              | 1234  | Open app → Local Server → Start                | In app → Stop Server                      |
| LiteLLM (Gemini proxy) | 4000  | `.venv/bin/litellm --config ...`               | Ctrl+C / stop.sh                          |
| Open WebUI             | 8080  | `DATA_DIR=... uvx ... open-webui@latest serve` | Ctrl+C / stop.sh                          |
| Pipelines              | 9099  | `cd .../pipelines → sh start.sh`               | Ctrl+C + `lsof -ti:9099 \| xargs kill -9` |
| Open Claw              | 18789 | `openclaw gateway start`                       | `openclaw gateway stop`                   |

---

## PART 11 — Voice-Memo Skill (Current Architecture)

> Production-grade ASR pipeline for academic lecture content.  
> Local-first · core/ shared framework · 6 Phases · MLX-Whisper · No Docker runtime

### 11.0 Architecture Overview

**Pipeline flow:** M4A → Transcript → Proofread → Merge → Highlight → Notion MD

All phases are implemented as `PipelineBase` subclasses importing from `core/`. The old `py_tools/` flat structure has been replaced by the current modular layout.

### 11.1 Directory Structure (Current)

```
open-claw-sandbox/
├── core/                          # Shared framework (all skills import from here)
│   ├── pipeline_base.py           # Abstract base for all Phase scripts
│   ├── state_manager.py           # Progress tracking + checklist.md rendering
│   ├── path_builder.py            # Config-driven path resolver
│   ├── llm_client.py              # OllamaClient with retry logic
│   ├── atomic_writer.py           # Corruption-safe file writes
│   ├── diff_engine.py             # DiffEngine + AuditEngine (Review Board)
│   ├── glossary_manager.py        # Cross-skill terminology sync
│   ├── inbox_daemon.py            # Inbox watchdog (auto-trigger)
│   └── web_ui/app.py              # Flask Dashboard (port 5001)
│
├── skills/
│   └── voice-memo/
│       ├── SKILL.md               # Quick-start reference
│       ├── config/
│       │   ├── config.yaml        # Model profiles, paths, hardware thresholds
│       │   └── prompt.md          # LLM prompts for Phase 2–5
│       ├── docs/
│       │   ├── ARCHITECTURE.md
│       │   └── DECISIONS.md
│       └── scripts/
│           ├── run_all.py         # Orchestrator (interactive, resume, force)
│           └── phases/
│               ├── p00_glossary.py    # Phase 0: Terminology initialisation
│               ├── p01_transcribe.py  # Phase 1: MLX-Whisper transcription
│               ├── p02_proofread.py   # Phase 2: LLM proofreading + term guard
│               ├── p03_merge.py       # Phase 3: Cross-chunk merge
│               ├── p04_highlight.py   # Phase 4: Key-concept highlighting
│               └── p05_synthesis.py   # Phase 5: Notion-ready synthesis
│
└── data/voice-memo/               # Runtime data (auto-created, not in git)
    ├── input/<subject>/*.m4a      # Drop audio files here
    ├── output/
    │   ├── 01_transcript/<subject>/
    │   ├── 02_proofread/<subject>/
    │   ├── 03_merged/<subject>/
    │   ├── 04_highlighted/<subject>/
    │   └── 05_notion_synthesis/<subject>/
    └── state/
        ├── .pipeline_state.json   # Source of truth for task progress
        └── checklist.md           # Human-readable progress table
```

### 11.2 Environment Setup (One-Time)

```bash
# System dependencies (Homebrew)
brew install poppler tesseract tesseract-lang

# Python dependencies
cd ~/Desktop/local-workspace/open-claw-sandbox
pip3 install -r ops/requirements.txt

# Set environment variables (add to ~/.zshrc or local-workspace/start.sh)
export WORKSPACE_DIR="/Users/limchinkun/Desktop/local-workspace/open-claw-sandbox"
export HF_HOME="${WORKSPACE_DIR}/models"

# Smoke test
python3 skills/voice-memo/scripts/run_all.py --help
```

### 11.3 Execution Commands

```bash
cd ~/Desktop/local-workspace/open-claw-sandbox

# Run full pipeline (all subjects)
python3 skills/voice-memo/scripts/run_all.py

# Process specific subject only
python3 skills/voice-memo/scripts/run_all.py --subject 助人歷程

# Resume from last checkpoint (after interruption)
python3 skills/voice-memo/scripts/run_all.py --resume

# Force re-run (overwrite completed phases)
python3 skills/voice-memo/scripts/run_all.py --force

# Interactive model switching
python3 core/cli_config_wizard.py --skill voice-memo

# Check progress
cat data/voice-memo/state/checklist.md

# Open Review Board (diff UI in browser)
open http://localhost:5001
```

### 11.4 Phase Reference

| Phase | Script              | Function                                                            |
| :---: | :------------------ | :------------------------------------------------------------------ |
|  P0   | `p00_glossary.py`   | Terminology table initialisation — prevents LLM hallucinating terms |
|  P1   | `p01_transcribe.py` | MLX-Whisper Large v3 high-accuracy transcription                    |
|  P2   | `p02_proofread.py`  | LLM proofreading + terminology protection                           |
|  P3   | `p03_merge.py`      | Cross-chunk merge and refinement                                    |
|  P4   | `p04_highlight.py`  | Key-concept highlighting                                            |
|  P5   | `p05_synthesis.py`  | Notion-ready knowledge synthesis (Cornell + QEC + Feynman)          |

### 11.5 Core Design Decisions

| Decision                           | Rationale                                                                 |
| ---------------------------------- | ------------------------------------------------------------------------- |
| ① MLX-Whisper (not faster-whisper) | Apple Silicon native — 3–5× faster, no Docker needed                      |
| ② core/ shared framework           | All skills share PipelineBase, StateManager, AtomicWriter                 |
| ③ SHA-256 content audit            | Only reprocess if file content actually changed                           |
| ④ Atomic state persistence         | Write to disk before updating checklist — no false positives              |
| ⑤ config.yaml hot-switch           | Model profiles switchable without code changes                            |
| ⑥ Unified state per skill          | `data/voice-memo/state/` — single source of truth                         |
| ⑦ `{INPUT_CONTENT}` placeholder    | Injects transcript mid-prompt — counters Lost-in-the-Middle               |
| ⑧ Flat instruction format          | Numbered top-level list + (DO NOT SKIP) — prevents Gemma3 skipping blocks |

### 11.6 Config File Location

- **Main config**: `skills/voice-memo/config/config.yaml` — model profiles, paths, hardware thresholds
- **LLM prompts**: `skills/voice-memo/config/prompt.md` — Phase 2–5 system prompts
- **Model switch**: `python3 core/cli_config_wizard.py --skill voice-memo`

### 11.7 Troubleshooting

| Problem                            | Symptom                                   | Fix                                                                                           |
| ---------------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------------------- |
| Ollama connection failed           | `ConnectionRefusedError: 127.0.0.1:11434` | Confirm Ollama is running; `gemma3:12b` loaded                                                |
| Whisper model re-downloads         | Slow on every run                         | Confirm `HF_HOME` env var points to `models/`                                                 |
| Phase 5 outputs "Okay, Here is..." | LLM conversational filler                 | Check `prompt.md` bottom has CRITICAL FORMAT REQUIREMENT                                      |
| Phase 5 missing Cornell/Feynman    | Incomplete output                         | Ensure prompt list is numbered 1–7 top-level with (DO NOT SKIP)                               |
| Config profile switch ineffective  | Still uses old model                      | Run: `python3 -c "import yaml; yaml.safe_load(open('skills/voice-memo/config/config.yaml'))"` |
| Checklist false positive ✅         | Status shows done but output is empty     | Edit `.pipeline_state.json` manually; set phase back to `pending`                             |

---

## PART 11b — PDF Knowledge Skill (Current Architecture)

> Processes scanned or structured PDFs into unified Markdown knowledge bases.  
> Local-first · Docling extraction · VLM figure analysis · 7 Phases · Anti-Tampering highlights

### 11b.1 Architecture Overview

**Pipeline flow:** PDF → Diagnose → Extract → Vector Charts → OCR Gate → VLM Vision → Highlight → Synthesize → Markdown KB

### 11b.2 Directory Structure

```
skills/pdf-knowledge/
├── SKILL.md
├── config/
│   ├── config.yaml            # Paths, model profiles, OCR thresholds, chunk size
│   ├── priority_terms.json    # Cross-skill terminology (shared with voice-memo)
│   ├── security_policy.yaml   # PDF security scanning rules
│   └── selectors.yaml         # Data source selector configuration
├── docs/
│   ├── ARCHITECTURE.md
│   └── DECISIONS.md
└── scripts/
    ├── run_all.py             # QueueManager orchestrator: batch PDF queue processor
    └── phases/
        ├── p00a_diagnostic.py     # Phase 0a: Lightweight PDF diagnostic
        ├── p01a_engine.py         # Phase 1a: Docling deep extraction → raw_extracted.md (IMMUTABLE)
        ├── p01b_vector_charts.py  # Phase 1b: Vector chart rasterisation (pdftoppm)
        ├── p01c_ocr_gate.py       # Phase 1c: OCR quality assessment (scan PDFs only)
        ├── p01d_vlm_vision.py     # Phase 1d: VLM visual figure description → figure_list.md
        ├── p02_highlight.py       # Phase 2: LLM Anti-Tampering highlights → highlighted.md
        └── p03_synthesis.py       # Phase 3: Map-Reduce synthesis → content.md

data/pdf-knowledge/
├── input/<subject>/*.pdf          # Drop PDF files here (by subject)
├── output/
│   ├── 02_Processed/<subject>/<id>/   # Docling extraction (IMMUTABLE — do not edit)
│   │   ├── raw_extracted.md
│   │   ├── figure_list.md
│   │   └── figures/
│   ├── 05_Final_Knowledge/<subject>/<id>/content.md   # Final output
│   ├── Error/                         # Failed PDFs quarantined here
│   └── vector_db/                     # ChromaDB vector store
└── state/
    ├── .pipeline_state.json
    └── checklist.md
```

### 11b.3 System Dependencies

```bash
# Required for PDF rasterisation + OCR
brew install poppler tesseract tesseract-lang

# Python packages (included in ops/requirements.txt)
# docling, pymupdf, pytesseract, chromadb, etc.
```

### 11b.4 Execution Commands

```bash
cd ~/Desktop/local-workspace/open-claw-sandbox

# Drop PDF into Inbox first:
cp textbook.pdf data/pdf-knowledge/input/AI_Papers/

# Run full pipeline
python3 skills/pdf-knowledge/scripts/run_all.py

# Process specific subject only
python3 skills/pdf-knowledge/scripts/run_all.py --subject AI_Papers

# Interactive mode (pause after Phase 1d for human chart review)
python3 skills/pdf-knowledge/scripts/run_all.py --interactive

# Interactive model switching
python3 core/cli_config_wizard.py --skill pdf-knowledge

# Check progress
cat data/pdf-knowledge/state/checklist.md

# Open Review Board
open http://localhost:5001
```

### 11b.5 Phase Reference

| Phase | Script                  | Function                                                         |
| :---: | :---------------------- | :--------------------------------------------------------------- |
|  P0a  | `p00a_diagnostic.py`    | Lightweight diagnosis — page count, text density, scan detection |
|  P1a  | `p01a_engine.py`        | Docling deep extraction → `raw_extracted.md` **(IMMUTABLE)**     |
|  P1b  | `p01b_vector_charts.py` | Vector chart rasterisation via `pdftoppm`                        |
|  P1c  | `p01c_ocr_gate.py`      | OCR quality assessment (only triggered for scanned PDFs)         |
|  P1d  | `p01d_vlm_vision.py`    | VLM visual figure auto-description → `figure_list.md`            |
|  P2   | `p02_highlight.py`      | LLM Anti-Tampering key-point highlights → `highlighted.md`       |
|  P3   | `p03_synthesis.py`      | Map-Reduce knowledge synthesis → `content.md`                    |

> ⚠️ **IMMUTABLE rule**: `raw_extracted.md` (P1a output) must NEVER be modified by downstream phases. It is the permanent source record.

### 11b.6 Troubleshooting

| Problem                                 | Fix                                                    |
| --------------------------------------- | ------------------------------------------------------ |
| `poppler not found`                     | `brew install poppler`                                 |
| Docling model re-downloads on every run | Confirm `HF_HOME` env var → `models/`                  |
| VLM Phase 1d skipped (no figures)       | Expected — only runs when diagnostic detects figures   |
| OCR gate triggers unexpectedly          | Check `config.yaml` `ocr.text_density_threshold`       |
| Failed PDFs not quarantined             | Check `Error/` dir; re-run with `--force` after fixing |

---




## PART 12 — Notion Integration

### 12.1 Setup Notion MCP Server

1. Go to https://www.notion.so/my-integrations → Create new integration → name it `AI Ecosystem` → save the Integration Secret Key
2. Share your target Notion pages/databases with this integration: Page → Share → Invite → your integration name
3. Add the key to `.vscode/mcp.json` (already shown in Part 6) and to docker-compose.yml for Open Claw

### 12.2 Recommended Notion Database Structure

| Database Name  | Content Archived                       | Agent That Updates It |
| -------------- | -------------------------------------- | --------------------- |
| Project Log    | PROGRESS.md content, session summaries | Cline / Open Claw     |
| Task Board     | TASKS.md active + completed tasks      | Cline / Antigravity   |
| Decision Log   | DECISIONS.md architectural choices     | Antigravity           |
| Research Notes | PDF-to-Markdown outputs, lecture notes | Open Claw overnight   |
| Code Snippets  | Reusable functions, config templates   | Cline                 |

### 12.3 Cline Notion Archiving Command

At session end, add this to your closing prompt:

```
Archive today's session to Notion:
1. Add a new entry to Project Log: date, tasks completed, blockers
2. Move completed Task Board items from In Progress to Done
3. If any architectural decision was made, add it to Decision Log
```

---

## PART 13 — Additional Automation Workflows

### 13.1 Vision-to-Markdown Workflow

Converts PDFs (including those with charts, tables, and figures) into clean, structured Markdown with AI-extracted insights.

| Step                 | Tool                    | Output                         |
| -------------------- | ----------------------- | ------------------------------ |
| 1. PDF → images      | pymupdf (Python)        | High-res PNG per page          |
| 2. Text extraction   | pdfplumber (Python)     | Raw text + table coordinates   |
| 3. Figure analysis   | Gemini 2.5 Pro (vision) | Description + data extraction  |
| 4. Markdown assembly | LM Studio Phi-4-mini    | Clean structured Markdown      |
| 5. Key takeaways     | LM Studio Phi-4-mini    | ⭐ highlighted important points |
| 6. Archive           | Notion MCP              | Published to Notion page       |

```python
# Save as: ~/ai-workspace/scripts/pdf_to_markdown.py
import fitz, pdfplumber, requests, json
from pathlib import Path

def pdf_to_markdown(pdf_path: str, importance_keywords: list = None) -> str:
    """Convert PDF to structured Markdown with AI analysis."""
    pdf = Path(pdf_path)
    output = []

    with pdfplumber.open(pdf) as doc:
        for i, page in enumerate(doc.pages):
            text = page.extract_text() or ''
            tables = page.extract_tables()
            output.append(f'\n## Page {i+1}\n')
            output.append(text)
            for table in tables:
                if table:
                    header = '│ ' + ' │ '.join(str(c) for c in table[0]) + ' │'
                    sep = '│' + '│'.join(['---']*len(table[0])) + '│'
                    rows = ['│ ' + ' │ '.join(str(c) for c in row) + ' │' for row in table[1:]]
                    output.extend([header, sep] + rows)

    combined = '\n'.join(output)
    keywords_str = ', '.join(importance_keywords) if importance_keywords else 'key definitions, conclusions, data'
    prompt = f'''Clean this extracted PDF text into structured Markdown.
Rules:
- Fix OCR errors and broken lines
- Preserve all tables in Markdown format
- Mark figures as [FIGURE: description]
- Add ⭐ before any sentence containing: {keywords_str}
- Add ## headers for major sections
TEXT: {combined[:15000]}'''

    resp = requests.post('http://localhost:1234/v1/chat/completions',
        json={'model': 'Phi-4-mini-instruct',
              'messages': [{'role': 'user', 'content': prompt}],
              'max_tokens': 4000})
    return resp.json()['choices'][0]['message']['content']
```

**Tips for Vision-to-Markdown:**
- Use Gemini 2.5 Pro for figure analysis (genuine multimodal understanding, ~3–5 API calls for a 30-page paper)
- Use `pdfplumber` (not vision models) for tables — it's more accurate for structured tabular data
- For tables: pdfplumber extracts coordinates; only send non-table pages to Gemini

### 13.2 Academic LaTeX Formatting Workflow

Converts raw notes or plain text into properly formatted academic LaTeX. Runs locally with zero API cost (Phi-4-mini handles it well).

**LaTeX Prompt Template (use in LM Studio or Open WebUI):**

```
You are an expert academic LaTeX formatter. Convert the following notes into
professional LaTeX suitable for a [COURSE TYPE] paper.

Requirements:
- Use \documentclass{article} with geometry, amsmath, booktabs, hyperref
- All equations must use proper LaTeX math environments ($...$ or \begin{equation})
- Tables → \begin{table}[h] with \toprule/\midrule/\bottomrule
- Citations → \cite{} with \bibliography at end
- Numbered sections with \section and \subsection
- Add \label and \ref for cross-references

Input notes:
[PASTE YOUR NOTES HERE]
```

> ✅ **Tip:** For physics/chemistry LaTeX with complex equations, use `Phi-4-reasoning-plus` instead of `Phi-4-mini-instruct`. The reasoning model handles multi-step derivations and chemical formulas significantly better.

---

## PART 14 — Feasibility & Optimisation Review

### 14.1 Bottleneck Analysis

| Bottleneck                              | Severity | Root Cause                             | Mitigation                                                          |
| --------------------------------------- | -------- | -------------------------------------- | ------------------------------------------------------------------- |
| 16GB RAM — only 1 large model at a time | HIGH     | Fundamental hardware limit             | Watchdog eviction + clear model assignment matrix                   |
| Antigravity credit depletion            | HIGH     | Google's March 2026 credit change      | Architecture never depends on it — use for hard tasks only          |
| Whisper transcription speed             | MEDIUM   | Large model is slow on 16GB            | Run overnight via Open Claw; use `medium` model for quick checks    |
| Gemini free tier (100 req/day)          | MEDIUM   | API rate limit                         | LiteLLM load balancing + Cost Guard = 300 effective req/day         |
| Open WebUI Pipeline install             | MEDIUM   | Pipelines add-on is experimental       | Fallback: use Open WebUI without pipelines — manual model selection |
| LM Studio ↔ Ollama dual service         | LOW      | Both use llama.cpp but different ports | No conflict: :1234 and :11434 are independent                       |
| Open Claw Docker networking             | LOW      | Docker host.docker.internal required   | Use `--add-host` flag shown in Part 11                              |

### 14.2 Specific Enhancements

#### For Audio Transcription (Accent + Poor Quality)

- Use `--prompt` parameter in Whisper: provide a vocabulary list of technical terms specific to your course. This dramatically reduces transcription errors for domain-specific content.
- Pre-process audio with ffmpeg: `ffmpeg -i input.m4a -af 'highpass=f=200,afftdn=nf=-25' output.wav` — removes background noise before Whisper processes it.
- For Mandarin/Cantonese accents: add `--language zh` to Whisper — performs significantly better than auto-detect for mixed-language content.

#### For RAM Optimisation on 16GB

- Enable Metal GPU acceleration: already configured in LM Studio. For Ollama, models use Metal by default on Apple Silicon.
- Close Chrome tabs before loading large models (`gemma3:12b` or `deepseek-r1:14b`). Chrome can consume 3–5GB with multiple tabs.
- Use KV cache quantisation 4-bit in LM Studio — reduces model footprint by ~30% with minimal quality loss.

---

## PART 15 — Scalability Framework

Every component in this system is modular. Adding new capabilities requires NO architectural changes — only additions.

### 15.1 Adding New MCP Servers

Only one file changes: `.vscode/mcp.json`. No code changes, no restarts of other services.

```json
// Example: adding Slack
"slack": {
  "command": "npx",
  "args": ["@modelcontextprotocol/server-slack"],
  "env": { "SLACK_BOT_TOKEN": "xoxb-your-token" }
}
```

### 15.2 Adding New Models

| To Add              | Command                                                              |
| ------------------- | -------------------------------------------------------------------- |
| New Ollama model    | `ollama pull <model-name>` — immediately available in Open WebUI     |
| New LM Studio model | Search → Download → Start Server (requires Local Server restart)     |
| New cloud provider  | Add to `litellm-config.yaml` — no Open WebUI restart needed          |
| New Gemini account  | Add to `litellm-config.yaml` model_list — instantly adds 100 req/day |

### 15.3 Adding New Automation Workflows

New automation workflows follow a 4-step pattern:
1. Write the Python or bash script in `~/ai-workspace/scripts/`
2. Mount the required directories in docker-compose.yml for Open Claw
3. Create a task template in `~/ai-workspace/tasks/`
4. Add a Telegram command trigger if you want on-demand execution

### 15.4 Future Upgrade Path

| Upgrade                | When to Consider                                       | Unlocks                                       |
| ---------------------- | ------------------------------------------------------ | --------------------------------------------- |
| RAM upgrade to 24GB    | When `deepseek-r1:14b` + Chrome together cause crashes | Run 14B model + browsing simultaneously       |
| claude.ai Pro ($20/mo) | When Antigravity limits block daily work               | Claude Code terminal agent + 5x more messages |
| Local Stable Diffusion | When vision-to-notes needs image generation            | Diagram generation from text descriptions     |
| AnythingLLM            | When RAG over large document libraries is needed       | Query 100+ PDFs as a knowledge base           |
| Dedicated NAS storage  | When paper/audio archives exceed 500GB                 | Unlimited long-term storage for Open Claw     |

### 15.5 Daily Workflow Summary

#### Morning Startup (3 minutes)
- Run `./start.sh` from `~/Desktop/local-workspace/`
- LM Studio: Start Server → select MLX model
- Check Telegram for Open Claw overnight completion reports
- Open VS Code → first message: session start mantra

#### During Work
- Routine coding → VS Code Cline + `qwen2.5-coder:7b` (zero cost, unlimited)
- Architecture / hard problems → Antigravity (rotate Chrome profiles)
- Long documents / PDFs → LM Studio with Phi-4-mini
- STEM reasoning → LM Studio with Phi-4-mini-reasoning
- Vision / figures → Open WebUI → `gemini-pro` model (1 Gemini req)

#### Session End (2 minutes)
- Tell any AI: `Update HANDOFF.md and PROGRESS.md to reflect what we just did`
- If architectural decision: `Add to DECISIONS.md`
- If using Antigravity: `Summarise this session into WALKTHROUGH_LOG.md`

---

## PART 16 — Emergency Cheat Sheet

| Problem                         | Symptom                                   | Fix                                                                                                         |
| ------------------------------- | ----------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Mac very slow                   | Everything lagging                        | `ollama ps` → `ollama stop MODEL` → wait 30s                                                                |
| Swap Used > 5GB                 | Activity Monitor shows red                | Close Chrome immediately → restart Mac if persists                                                          |
| LM Studio won't connect         | `Cannot connect to localhost:1234`        | Open LM Studio → Local Server → Start Server                                                                |
| Pipelines `No module psutil`    | Error loading RAM Safety Guard            | `cd .../pipelines; source .venv/bin/activate; uv pip install psutil`                                        |
| Pipelines 'No Valves to Update' | UI shows no settings                      | Rename class to `Pipeline`. Add type hint: `self.valves: self.Valves = self.Valves()` then delete+re-upload |
| Pipelines port still occupied   | `Address already in use` on port 9099     | `lsof -ti:9099 \| xargs kill -9` then `sh start.sh`                                                         |
| LiteLLM websockets error        | `ModuleNotFoundError: websockets`         | `uv pip install 'litellm[proxy]'` (not just `litellm`)                                                      |
| Open WebUI wrong version        | `Distribution not found: file:///lastest` | Fix typo: `@lastest` → `@latest`                                                                            |
| Open Claw sandbox missing       | Scripts not found in npm install          | Manually curl 4 files from GitHub (see Part 8.3)                                                            |
| Open Claw TUI pairing bug       | `Pairing required / local fallback`       | Use `openclaw dashboard` (Web UI) to approve pairing                                                        |
| Watchdog not found              | LaunchAgent fails to start                | Check path is `~/Desktop/local-workspace/watchdog.sh`                                                       |
| Open Claw acting wrong          | Unexpected actions via Telegram           | Send: `STOP current task immediately`                                                                       |

---

## ✅ The Two Most Important Habits

**SESSION START:**
> "Read ~/.claude_profile.md and CLAUDE.md. Then HANDOFF.md and PROGRESS.md. Tell me the active task and what was last done. Then we begin."

**SESSION END:**
> "Update HANDOFF.md and PROGRESS.md to reflect what we just did."

These 30-second habits keep the entire system's memory intact forever.

---

*AI Ecosystem Master Guide — Version 9*  
*Updated from V8 · Reflects current production architecture (April 2026)*  
*voice-memo skill (6 phases · MLX-Whisper) · pdf-knowledge skill (7 phases · Docling)*  
*core/ shared framework · Open Claw Dashboard :5001 · Inbox Daemon · 7-service start.sh*  
*MacBook Pro M5 · 16GB RAM · April 2026*

