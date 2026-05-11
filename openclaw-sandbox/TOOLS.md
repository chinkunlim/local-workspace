# TOOLS.md

## 1. Purpose

Workspace-specific operational environment facts for agents and operators.
Do not duplicate logic already in `skills/<skill>/docs/` or `docs/CODING_GUIDELINES.md`.

---

## 2. Local Service Endpoints

| Service | URL | Managed By |
|:---|:---|:---|
| Open Claw API Gateway | `http://127.0.0.1:18789` | `infra/scripts/start.sh` |
| Ollama API | `http://127.0.0.1:11434` | External — `infra/scripts/start.sh` |
| LiteLLM Proxy | `http://127.0.0.1:4000` | External — `infra/scripts/start.sh` |
| Open WebUI | `http://127.0.0.1:3000` | External — `infra/scripts/start.sh` |
| Pipelines | `http://127.0.0.1:9099` | External — `infra/scripts/start.sh` |

> Ollama is the primary **skill-runtime** dependency. Its availability is verified by `startup_check()` in each `run_all.py` orchestrator (calls `http://127.0.0.1:11434/api/tags`).

---

## 3. Key Paths

| Item | Path |
|:---|:---|
| Workspace root | `openclaw-sandbox/` |
| Shared core framework | `core/` (7 sub-packages: cli/, config/, state/, orchestration/, services/, ai/, utils/) |
| Audio-transcriber skill | `skills/audio_transcriber/` |
| Doc-parser skill | `skills/doc_parser/` |
| Universal Inbox | `data/raw/` (routed by `inbox_daemon`) |
| Audio runtime data | `data/audio_transcriber/` |
| PDF runtime data | `data/doc_parser/` |
| Obsidian Wiki Vault | `data/wiki/` |
| ChromaDB vector store | `data/doc_parser/output/vector_db/` |
| Ops & maintenance scripts | `ops/` (sandbox), `../ops/` (global) |
| Lifecycle scripts | `../infra/scripts/` |
| Model cache (HuggingFace) | `models/` — set via `HF_HOME` env var |
| Structure map | `docs/STRUCTURE.md` |

---

## 4. Environment Variables

| Variable | Default | Purpose |
|:---|:---|:---|
| `WORKSPACE_DIR` | auto-detected | Absolute path to `openclaw-sandbox/`; set by `infra/scripts/start.sh` |
| `HF_HOME` | `models/` | HuggingFace model cache location |
| `OPENCLAW_API_URL` | `http://127.0.0.1:18789` | Open Claw API gateway URL |
| `TELEGRAM_BOT_TOKEN` | (required) | Telegram bot token — from `.env` file, never commit |
| `TELEGRAM_CHAT_ID` | (required) | User's Telegram chat ID for HITL notifications |
| `OPENCLAW_ENABLE_LLMGUARD` | `1` | Enable LLMGuard prompt injection scanning (`0` to disable) |
| `OPENCLAW_LOG_JSON` | `0` | Enable structured JSON logging for upstream aggregation |

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
| MLX Whisper Large v3 | `models/models--mlx-community--whisper-large-v3-mlx/` | audio_transcriber P1 |
| Faster Whisper medium | Downloaded to `models/` on first run | audio_transcriber P1 fallback |
| Docling layout/models | `models/models--docling-*/` | doc_parser P1b |

---

## 7. Rules

1. Keep entries factual and concise.
2. Update when operational reality changes (hardware upgrade, new endpoint, new env var).
3. Do not add runtime logic here — this file is documentation only.
