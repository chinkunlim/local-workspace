# CLAUDE.md — Academic Transcription Matrix (V7.0 — OOP & DAG Cascade Edition)

## Project Identity

A high-fidelity academic transcription and knowledge synthesis matrix designed for Bachelor's and Master's level research. The system prioritises data integrity, contextual precision, and strict separation of concerns across a governed, five-phase processing pipeline. Each phase writes to its own numbered output directory; no phase reads from anything other than the immediately preceding phase's output.

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Pipeline Architecture** | **V7.0 OOP & DAG**: Component-level Object-Oriented base classes (`core/`), DAG Cascade Hash Tracking. |
| **Transcription Engine** | Dynamic: `faster-whisper` (CPU/`medium` or `large-v3`) or `mlx-whisper` (Apple Silicon MPS) |
| **Inference Engine** | Mac-local Ollama — `gemma3:12b` (default) / `qwen2.5:14b` or `qwen3:14b` (recommended for Chinese) |
| **Environment** | Pure macOS Native Execution — Docker virtualisation deprecated |
| **Config source** | `voice-memo/config.json` (one `phaseN` key per phase, 0–5) |
| **Prompt source** | `skills/voice-memo/scripts/prompt.md` (one `## Phase N` section per phase, 0–5) |

---

## Engineering Standards

### V7.0 DAG State Management
Atomic state updates are written to a centralised `.pipeline_state.json` after each successful file write. The system computes SHA-256 hashes for all intermediate Markdown outputs (`01_transcript` ~ `05_notion_synthesis`).
**Cascade Invalidation**: If an intermediate file is manually edited (hash mismatch), all dependent downstream phases are automatically marked as `⏳` (Pending) in the DAG. The human-readable `checklist.md` is strictly a read-only rendered view.

> [!IMPORTANT]
> ### V7.1 AI Collaboration & Local Git Sync
> All AI agents modifying this repository MUST push automatic local `git commits` after successful feature deployment to maintain immediate rollback states. The top-tier interaction protocol demands updating `HANDOFF.md`, `TASKS.md`, `PROGRESS.md`, `DECISIONS.md`, and `WALKTHROUGH.md` sequentially.

### Component-Level OOP (`core/` Framework)
All `_tool.py` scripts consist solely of prompt loading and execution flows by subclassing `PipelineBase`. 
- **`pipeline_base.py`**: Encapsulates tqdm progress UI, system health checking, prompt file routing, error trapping, and signal isolation (interruptions).
- **`state_manager.py`**: Manages `.pipeline_state.json`, cascade invalidation logic, and rendering `checklist.md`.
- **`llm_client.py`**: Abstracted `requests` wrapper with timeout parameters, multi-try retry mechanisms, and memory dumping features (`keep_alive: 0`).

### Hardware Defence Metrics

> [!WARNING]
> | Level | Condition |
> | :--- | :--- |
> | ⚠️ Warning | Available RAM < 1 GB (macOS native), Temp > 85 °C, Battery < 15 % |
> | 🚨 Critical | Available RAM < 300 MB (macOS native), Disk < 200 MB, Temp > 95 °C, Battery < 5 % |

---

## 5-Phase Pipeline Architecture & Python Scripts

```
raw_data/
  └─ <Subject>/  *.m4a  *.pdf  glossary.json (user-curated OR auto-generated)
        │
        ▼  Phase 0 (glossary_tool.py)
        │
        ▼  Phase 1 (transcribe_tool.py)
01_transcript/
        │
        ▼  Phase 2 (proofread_tool.py)
02_proofread/
        │
        ▼  Phase 3 (merge_tool.py)
03_merged/
        │
        ▼  Phase 4 (highlight_tool.py)
04_highlighted/
        │
        ▼  Phase 5 (notion_synthesis.py)
05_notion_synthesis/
```

### Script Purposes (`scripts/` directory)

| Component | Script Name | Purpose |
| :---: | :--- | :--- |
| **Framework** | `core/pipeline_base.py` | Pipeline base class defining IO templates and interrupt safeties for all agents. |
| **Framework** | `core/state_manager.py` | State persistence. Computes hashes and flips downstream DAG statuses to Pending `⏳`. |
| **Framework** | `core/llm_client.py` | HTTP driver to Ollama. Manages automated retries on timeout. |
| **Agent** | `run_all.py` | Orchestrator. Checks dependencies, creates interactive Dashboard, and loops all phase scripts. |
| **Phase 0** | `glossary_tool.py` | Given P1 outputs, uses LLM to identify Whisper hallucinated words and saves to `glossary.json`. |
| **Phase 1** | `transcribe_tool.py` | Uses `mlx-whisper` / `faster-whisper` to generate base plaintext transcripts. |
| **Phase 2** | `proofread_tool.py` | Contextual proofreader validating transcript vs user PDF syllabus. Verbatim Guard checks output len. |
| **Phase 3** | `merge_tool.py` | Merges `.md` file segments (L01-1, L01-2) back into full lectures (L01). Paragraphing/Speaker diarization. |
| **Phase 4** | `highlight_tool.py` | Inserts `**bold**`, `==highlight==` without deleting text. Anti-Tampering (0.95 verbatim) applied. |
| **Phase 5** | `notion_synthesis.py` | Map-Reduce long documents. Synthesizes Cornell, Feynman formats. *Uses Agentic Self-Correction Loop for Mermaid Syntax*. |

---

## Operations & Debugging

```bash
# Recommended: Full Pipeline (Orchestrator) - Automatically skips completed stages
python3 /Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/run_all.py

# Recreate checklist from physical files
python3 .../skills/voice-memo/scripts/reconcile_state.py
```