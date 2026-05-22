# ARCHITECTURE.md — proofreader Skill

> **Version**: V1.0 | **Last Updated**: 2026-05-23

## 1. Role

The `proofreader` is the **Layer 3 quality gate** in the Open Claw pipeline. It sits between raw extraction skills (`audio_transcriber`, `doc_parser`) and the verified knowledge store (`04_final_verified/`).

Its defining architectural characteristic is **Non-Blocking HITL**: it never holds the pipeline thread open waiting for human approval. Instead, it serializes a "pending chain" and releases all VRAM, allowing the user to review on their own schedule.

---

## 2. Pipeline Position

```
audio_transcriber  ──┐
                     ├──▶  proofreader  ──▶  04_final_verified/  ──▶  Sequential SSoT Chain
doc_parser         ──┘         │
                               │ (HITL Gate — Non-Blocking)
                               ▼
                        pending_chains.json
                               │
                        Dashboard (localhost:5000)
                               │
                        Human Approves / Edits
                               │
                               ▼
                        04_final_verified/<Subject>/
                               │
                        inbox_daemon watchdog resumes chain
```

---

## 3. Proofreading Modes

| Mode | Trigger | Description |
|:---|:---|:---|
| **Mode A** (1-to-1) | Single source (audio OR doc) | Full-draft grammar and terminology correction |
| **Mode B** (1-to-many) | Single source, consensus vote | Paragraph-level majority vote across 3 lightweight LLMs — catches systematic errors |
| **Mode C** (many-to-1) | Both audio + doc for same Subject | Cross-source vocabulary calibration — aligns terminology between slide deck and lecture audio |

Mode is determined automatically by `RouterAgent` based on the `pending_chains.json` manifest.

---

## 4. HITL Dashboard (Non-Blocking)

- Served at `http://localhost:5000` via `scripts/dashboard.py`
- **Left Pane**: Embedded Ground Truth viewer — renders original PDF, PNG, or Audio player (`.m4a`)
- **Right Pane**: Monaco editor with the AI-corrected Markdown draft
- **Actions**: ✅ Approve, ✏️ Edit + Approve, ⏭️ Skip & Forward (bypasses this file, resumes chain without it), ❌ Reject
- Upon Approve, writes output to `data/proofreader/output/04_final_verified/<Subject>/`
- Upon completion, `inbox_daemon` watchdog detects the new verified file and resumes the suspended `pending_chains.json` entry

---

## 5. HITL Interrupt Flow

```python
# proofreader raises HITLPendingInterrupt after writing pending_chains.json
raise HITLPendingInterrupt(chain_id=chain_id, subject=subject)

# RouterAgent catches it:
except HITLPendingInterrupt as e:
    # Serialize remaining chain to pending_chains.json
    # Release VRAM by destroying skill runner context
    # Notify user via Telegram + Dashboard URL
    return  # releases pipeline thread
```

---

## 6. Pending Chain Contract

`data/proofreader/output/pending_chains/<chain_id>.json`:

```json
{
  "chain_id": "uuid",
  "subject": "SubjectName",
  "source_skill": "audio_transcriber|doc_parser",
  "input_path": "data/proofreader/output/<subject>/draft_<uuid>.md",
  "ground_truth_path": "data/audio_transcriber/output/03_merged/<subject>/...",
  "remaining_chain": ["smart_highlighter", "note_generator", "feynman_simulator", "academic_edu_assistant"],
  "created_at": "ISO8601"
}
```

---

## 7. Core Framework Dependencies

| Module | Usage |
|:---|:---|
| `core.orchestration.pipeline_base.PipelineBase` | All phase class inheritance |
| `core.state.state_manager.StateManager` | Phase progress tracking |
| `core.utils.atomic_writer.AtomicWriter` | Crash-safe file writes |
| `core.services.hitl_manager.HITLManager` | Interrupt serialization + Telegram notification |
| `core.ai.llm_client.OllamaClient` | Proofreading LLM calls (via `self.llm`) |

---

## 8. Key Invariants

1. **Non-blocking**: `proofreader` MUST NOT hold a thread waiting for human input. Use `HITLPendingInterrupt`.
2. **Immutable source**: The draft written to `output/<subject>/` is the AI output. Ground Truth is read-only.
3. **Verified output is SSoT**: `04_final_verified/<Subject>/` is the canonical source for all downstream modules.
4. **Chain serialization**: Remaining chain steps are ALWAYS serialized to `pending_chains.json` before interrupt.
5. **Watchdog resume**: `inbox_daemon` is the only authorized resumption trigger — never call `RouterAgent.resume()` directly from dashboard code.
