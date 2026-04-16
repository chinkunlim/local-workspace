# TOOLS.md

## 1. Purpose

Workspace-specific operational environment facts for agents and operators.
Do not duplicate logic already in `skills/<skill>/docs/` or `docs/CODING_GUIDELINES.md`.

---

## 2. Local Service Endpoints

| Service | URL | Managed By |
|:---|:---|:---|
| Open Claw Dashboard | `http://127.0.0.1:5001` | `core/web_ui/app.py` |
| Ollama API | `http://127.0.0.1:11434` | External — `local-workspace/start.sh` |
| LiteLLM / Gemini Gate | `http://127.0.0.1:4000` | External — `local-workspace/start.sh` |
| Open WebUI | `http://127.0.0.1:8080` | External — `local-workspace/start.sh` |

> Ollama is the only **skill-runtime** dependency. Its availability is verified by `startup_check()` in each `run_all.py` orchestrator.

---

## 3. Key Paths

| Item | Path |
|:---|:---|
| Workspace root | `open-claw-workspace/` |
| Shared core framework | `core/` |
| Voice-memo skill | `skills/voice-memo/` |
| PDF-knowledge skill | `skills/pdf-knowledge/` |
| Voice-memo runtime data | `data/voice-memo/` |
| PDF-knowledge runtime data | `data/pdf-knowledge/` |
| Ops & maintenance scripts | `ops/` |
| Model cache (HuggingFace) | `models/` — set via `HF_HOME` env var |
| Structure map | `docs/STRUCTURE.md` |

---

## 4. Environment Variables

| Variable | Default | Purpose |
|:---|:---|:---|
| `WORKSPACE_DIR` | auto-detected | Absolute path to `open-claw-workspace/`; set by `local-workspace/start.sh` |
| `HF_HOME` | `models/` | HuggingFace model cache location |
| `DASHBOARD_HOST` | `127.0.0.1` | Flask dashboard bind host |
| `DASHBOARD_PORT` | `5001` | Flask dashboard bind port |

---

## 5. Hardware Profile

| Item | Value |
|:---|:---|
| RAM | 16 GB |
| Chip | Apple Silicon (MPS available for MLX) |
| OS | macOS |

Hardware safety thresholds (RAM warning/critical, temperature, battery) are configured per skill in `skills/<skill>/config/config.yaml` under `hardware:`.

---

## 6. Model Locations

| Model | Location | Used By |
|:---|:---|:---|
| Ollama models (Gemma, Qwen…) | Ollama app data (outside workspace) | All LLM phases |
| MLX Whisper Large v3 | `models/models--mlx-community--whisper-large-v3-mlx/` | voice-memo P1 |
| Faster Whisper medium | Downloaded to `models/` on first run | voice-memo P1 fallback |
| Docling layout/models | `models/models--docling-*/` | pdf-knowledge P1b |

---

## 7. Rules

1. Keep entries factual and concise.
2. Update when operational reality changes (hardware upgrade, new endpoint, new env var).
3. Do not add runtime logic here — this file is documentation only.
