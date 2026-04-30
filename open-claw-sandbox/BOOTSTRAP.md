# BOOTSTRAP.md

## 1. Purpose

Bring `open-claw-sandbox` to a fully operational state on macOS from a clean clone.
This workspace is a self-contained sandbox. No external secrets or lifecycle scripts are required to run the pipelines.

---

## 2. System Dependencies

Install these once via Homebrew:

```bash
# Required: PDF rasterisation + OCR
brew install poppler tesseract tesseract-lang

# Required: verify Python 3.11+ is available
python3 --version

# Required: pip-tools for reproducible dependency locking
pip3 install pip-tools
```

---

## 3. Python Dependencies

```bash
cd /Users/limchinkun/Desktop/local-workspace/open-claw-sandbox

# Install all locked dependencies via pip-tools (reproducible builds)
pip-sync requirements.txt

# Install code quality tools (if not already in requirements.txt)
pip3 install ruff mypy pre-commit
```

Or use the automated bootstrap script:

```bash
bash ops/bootstrap.sh
```

> **Note**: `requirements.txt` is generated from `requirements.in` via `pip-compile`.
> To update dependencies: edit `requirements.in`, then run `pip-compile requirements.in`.

---

## 4. Set Up Code Quality Hooks (Optional but Recommended)

```bash
# Install pre-commit hooks (runs Ruff on every git commit)
pre-commit install -c ops/config/.pre-commit-config.yaml

# Verify all checks pass on current codebase
./ops/check.sh
```

---

## 5. Configure Environment Variable

The workspace auto-detects its own path using `core/bootstrap.py` directory traversal.
For explicit configuration (e.g. in shell profiles or `start.sh`), set:

```bash
export WORKSPACE_DIR="/Users/limchinkun/Desktop/local-workspace/open-claw-sandbox"
export HF_HOME="${WORKSPACE_DIR}/models"   # keep model cache inside workspace
```

---

## 6. Verify Installation

```bash
# Smoke-test: confirm all core sub-packages import cleanly
python3 -c "
from core.utils.bootstrap import ensure_core_path
ensure_core_path('.')
from core.orchestration.pipeline_base import PipelineBase
from core.state.state_manager import StateManager
from core.utils.path_builder import PathBuilder
from core.utils.diff_engine import DiffEngine, AuditEngine
from core.services.inbox_daemon import SystemInboxDaemon
from core.ai.llm_client import OllamaClient
print('✅ core: all sub-packages OK')
"

# Smoke-test: audio-transcriber CLI
python3 skills/audio-transcriber/scripts/run_all.py --help

# Smoke-test: doc-parser CLI
python3 skills/doc-parser/scripts/run_all.py --help

# Smoke-test: Open Claw API gateway (started by infra/scripts/start.sh)
curl -s http://127.0.0.1:18789/health || echo 'API not running — start with ../infra/scripts/start.sh'
```

---

## 7. Skill Data Directories

Directories are created automatically on first pipeline run.
Drop files here to begin processing:

| Skill | Input location |
|:---|:---|
| **Universal Inbox** (recommended) | `data/raw/<subject>/` — `inbox_daemon` routes automatically |
| audio-transcriber (direct) | `data/audio-transcriber/input/<subject>/*.m4a` |
| doc-parser (direct) | `data/doc-parser/input/<subject>/*.pdf` |

---

## 8. Documentation Baseline

After bootstrap, read in this order:

1. `../docs/INDEX.md` — master documentation map
2. `../docs/STRUCTURE.md` — annotated map of every file and folder
3. `../docs/CODING_GUIDELINES_FINAL.md` — binding engineering contract
4. `AGENTS.md` — agent operation rules
5. `skills/<skill>/SKILL.md` — skill quick-start guide
6. `skills/<skill>/docs/ARCHITECTURE.md` — full technical architecture

---

## 9. Starting the Full AI Ecosystem

The broader AI stack (Ollama, Open WebUI, LiteLLM, Open Claw gateway) is managed
by `local-workspace/infra/scripts/start.sh` and `stop.sh` — outside this sandbox.

```bash
# Start all services (run from local-workspace/ root)
../infra/scripts/start.sh

# Stop all services
../infra/scripts/stop.sh

# RAM watchdog (auto-evicts models when memory drops below 15%)
../infra/scripts/watchdog.sh

# Open Claw API gateway endpoint (after start.sh)
curl http://127.0.0.1:18789/health
```

> The legacy Flask dashboard (`core/web_ui/app.py`) has been **deprecated** and removed.
> All pipeline orchestration is now via the Open Claw CLI and Telegram bot interface.
