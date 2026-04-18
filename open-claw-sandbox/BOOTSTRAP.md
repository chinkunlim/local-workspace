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

# Required: verify Python 3.9+ is available
python3 --version
```

---

## 3. Python Dependencies

```bash
cd /Users/limchinkun/Desktop/local-workspace/open-claw-sandbox

# Install all skill and core dependencies
pip3 install -r ops/requirements.txt

# Install code quality tools
pip3 install ruff mypy pre-commit
```

Or use the automated bootstrap script (if available):

```bash
bash ops/bootstrap.sh
```

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
# Smoke-test: confirm all core modules import cleanly
python3 -c "
from core.bootstrap import ensure_core_path
ensure_core_path('.')
from core import (PipelineBase, StateManager, PathBuilder,
                  DiffEngine, AuditEngine, SystemInboxDaemon)
print('✅ core: all modules OK')
"

# Smoke-test: voice-memo CLI
python3 skills/voice-memo/scripts/run_all.py --help

# Smoke-test: pdf-knowledge CLI
python3 skills/pdf-knowledge/scripts/run_all.py --help

# Smoke-test: dashboard
python3 core/web_ui/app.py &
curl -s http://127.0.0.1:5001/api/status | python3 -m json.tool
kill %1
```

---

## 7. Skill Data Directories

Directories are created automatically on first pipeline run.
Drop files here to begin processing:

| Skill | Input location |
|:---|:---|
| voice-memo | `data/voice-memo/input/raw_data/<subject>/*.m4a` |
| pdf-knowledge | `data/pdf-knowledge/input/01_Inbox/<subject>/*.pdf` |

---

## 8. Documentation Baseline

After bootstrap, read in this order:

1. `docs/STRUCTURE.md` — annotated map of every file and folder
2. `docs/CODING_GUIDELINES.md` — binding engineering contract
3. `AGENTS.md` — agent operation rules
4. `skills/<skill>/SKILL.md` — skill quick-start guide
5. `skills/<skill>/docs/ARCHITECTURE.md` — full technical architecture

---

## 9. Starting the Full AI Ecosystem

The broader AI stack (Ollama, Open WebUI, LiteLLM, Open Claw gateway) is managed
by `local-workspace/start.sh` and `local-workspace/stop.sh` — outside this workspace.

To start only the Open Claw Dashboard independently:

```bash
python3 core/web_ui/app.py
# → http://127.0.0.1:5001
```
