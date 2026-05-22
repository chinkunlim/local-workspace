# ARCHITECTURE.md — student_researcher Skill

> **Version**: V1.0 | **Last Updated**: 2026-05-23

## 1. Role

`student_researcher` is the **Multi-Ingress Funnel** for academic deep research. It is the **only skill that accepts inputs from multiple independent source streams simultaneously**. It is **manually triggered only** — it never executes automatically as part of any chain.

---

## 2. Multi-Ingress Sources

```
Source 1: Chat/Q&A Markdown  ──┐
  (data/raw/<Subject>/*.md)    │
                               │   Staging Area
Source 2: Telegram /idea  ─────├──▶  data/student_researcher/input/<Subject>/
  (voice note or text capture) │                    │
                               │           Manual Trigger Only
Source 3: Verified Transcript  │     uv run skills/student_researcher/
  (04_final_verified/<Subj>/) ─┘            scripts/run_all.py --process-all
```

**Critical invariant**: All three source streams write to the **staging area** only. No processing occurs until the user explicitly invokes `run_all.py`. The `inbox_daemon` and `RouterAgent` are NOT authorized to trigger `student_researcher`.

---

## 3. Pipeline Phases

| Phase | Script | Description |
|:---|:---|:---|
| **P00** | `p00_context_search.py` | ChromaDB semantic search on existing wiki to find related knowledge. Generates `[[WikiLinks]]` for connected notes. Orphaned claims get `#incubating` tag → `wiki/Incubator/`. |
| **P01** | `p01_claim_extraction.py` | `deepseek-r1:8b` CoT reasoning identifies which claims need academic verification. Produces structured claim list with confidence score + verification priority. |
| **P02** | `p02_synthesis.py` | Orchestrates `academic_library_agent` (paper retrieval) and `gemini_verifier_agent` (AI debate). Synthesizes final Verification Report. |

---

## 4. Downstream Skill Delegation

```
student_researcher P02
     │
     ├──▶  academic_library_agent  (Playwright browser retrieval)
     │         │
     │         └──▶  PDF/text snapshots → data/student_researcher/evidence/
     │
     └──▶  gemini_verifier_agent   (3-round AI debate)
               │
               └──▶  Verification Report → data/student_researcher/output/
```

---

## 5. Output Format

Each processed subject produces:
- `data/student_researcher/output/<Subject>/verification_report.md` — claim-by-claim evidence summary
- `data/student_researcher/output/<Subject>/wiki_links.md` — ChromaDB-linked related notes
- `data/student_researcher/evidence/<Subject>/` — raw PDFs + text snapshots from `academic_library_agent`

---

## 6. Core Framework Dependencies

| Module | Usage |
|:---|:---|
| `core.orchestration.pipeline_base.PipelineBase` | All phase class inheritance |
| `core.state.state_manager.StateManager` | Phase progress tracking |
| `core.utils.atomic_writer.AtomicWriter` | Crash-safe output writes |
| `core.ai.llm_client.OllamaClient` | `deepseek-r1:8b` via `self.llm` |
| `core.ai.hybrid_retriever.HybridRetriever` | ChromaDB semantic search for P00 |

---

## 7. Key Invariants

1. **Manual trigger only**: `student_researcher` MUST NOT appear in any `_DEFAULT_CHAINS` in `RouterAgent`. It is never enqueued automatically.
2. **Staging never auto-processes**: Files in `data/student_researcher/input/` sit inert until `run_all.py` is invoked.
3. **`self.llm` reuse**: Never instantiate `OllamaClient()` manually — always use `self.llm` from `PipelineBase` (CODING_GUIDELINES §8.1).
4. **Structured logging only**: No bare `print()` calls — use `self.info()`, `self.error()`, `self.warning()` (CODING_GUIDELINES §8.1).
5. **Memory safety**: `asyncio.Semaphore(1)` enforced for all LLM calls — prevents OOM on 16 GB Apple Silicon.
