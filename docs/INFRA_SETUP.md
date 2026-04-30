# Open Claw — 3rd-Party Infrastructure Setup

> This document contains the installation and configuration instructions for the underlying third-party infrastructure (Ollama, LM Studio, Open WebUI, LiteLLM, MCP Servers).

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
# Pull all models (Full command, ensures fetching latest version)
ollama pull qwen2.5-coder:7b
ollama pull deepseek-r1:8b
ollama pull gemma3:12b
ollama pull deepseek-r1:14b
ollama pull qwen3.5:9b

# If you need a specific quantised version (GGUF), download via huggingface-cli manually and create Modelfile
# Example: huggingface-cli download unsloth/DeepSeek-R1-GGUF --include "*Q4_K_M.gguf"
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
# Option A: Start directly with uvx (Recommended for macOS local env)
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
# Option B: Deploy via Docker (If containerised env is needed)
# ==========================================
# Must use --network host (Linux) or map ports correctly to reach localhost Ollama
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

> **🔗 infra/scripts/ Integration Mechanism**：In daily operations, you should not start Pipeline manually. Always use `infra/scripts/start.sh`，it automatically provisions Pipeline andall infrastructure establishes correct backgroundExecution threads and log binding。

Manual test commands are as follows:
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
Open WebUI Pipeline: RAM Safety Guard (Memory Safety Guard)
Function: Automatically checks Mac's available physical memory (RAM) before sending conversation requests.
If available RAM is below the warning threshold, and the user selected a heavy model,
The system will automatically intercept the request and force a fallback to a lightweight safety model to prevent system freeze.
Dependencies: uv pip install psutil
"""
import psutil
from typing import Optional
from pydantic import BaseModel, Field

class Pipeline:
    """
    Core pipeline class.
    Note: Open WebUI mandates the main class must be named 'Pipeline', cannot use 'Filter'.
    """
    class Valves(BaseModel):
        ram_threshold_mb: int = Field(default=4000, description='Low memory warning threshold (MB)')
        safety_model: str = Field(default='qwen2.5-coder:7b', description='Lightweight fallback model when warning triggered')

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
Open WebUI Pipeline: Gemini Cost Guard (API Quota Guard)
Function: Automatically tracks and limits daily Gemini API calls.
When daily usage reaches the limit (default 270), the system intercepts and forwards to local fallback model.
"""
import json
import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

class Pipeline:
    class Valves(BaseModel):
        daily_limit: int = Field(default=270, description='Daily Gemini API request limit')
        safety_buffer: int = Field(default=30, description='Reserved safety buffer count')
        fallback_model: str = Field(default='qwen2.5-coder:7b', description='Fallback model when quota is exhausted')
        quota_file_path: str = Field(
            default='/tmp/gemini_quota.json',  # /tmp works in Docker containers
            description='Quota tracking JSON file path'
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

