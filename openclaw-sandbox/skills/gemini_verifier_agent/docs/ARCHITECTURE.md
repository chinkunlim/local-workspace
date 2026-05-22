# ARCHITECTURE.md — gemini_verifier_agent Skill

> **Version**: V1.0 | **Last Updated**: 2026-05-23

## 1. Role

`gemini_verifier_agent` is a **Cloud-Local AI Debate** skill. It pits a local `deepseek-r1:8b` (Student/Challenger role) against cloud Gemini (Tutor/Defender role) in a structured multi-round Socratic debate, producing an evidence-graded Verification Report.

It is a **sub-skill**: only `student_researcher` invokes it. It is never triggered by `RouterAgent` or `inbox_daemon` directly.

---

## 2. Debate Architecture

```
student_researcher (claim list + evidence)
        │
        ▼
gemini_verifier_agent
        │
        ├── Round 1: Gemini presents evidence FOR the claim
        │       └── deepseek-r1:8b challenges with counter-evidence + CoT reasoning
        │
        ├── Round 2: Gemini defends / updates position
        │       └── deepseek-r1:8b refines challenge
        │
        ├── Round 3: Final synthesis
        │       └── deepseek-r1:8b produces verdict with evidence citations
        │
        └──▶ Verification Report: data/student_researcher/output/<Subject>/verification_report.md
```

---

## 3. Model Assignment

| Role | Model | Why |
|:---|:---|:---|
| **Tutor (Defender)** | Cloud Gemini (via Playwright) | Broad academic knowledge, authoritative sourcing |
| **Student (Challenger)** | `deepseek-r1:8b` (local Ollama) | Native `<think>` CoT tokens enable genuine Socratic argumentation |

---

## 4. Gemini Access Strategy

- Playwright persistent browser context in `data/gemini_verifier_agent/browser_context/`
- Accesses `gemini.google.com` (consumer interface, no API key required)
- Session-based: first run requires manual login; subsequent runs reuse session
- **Fragility note**: Playwright scraping is inherently fragile. If the UI changes, `p01_ai_debate.py` page selectors must be updated. See DECISIONS.md for the rationale for choosing Playwright over Gemini API.

---

## 5. Verification Report Format

```markdown
# Verification Report — <Subject> / <Claim ID>

## Claim
<original claim text>

## Evidence For
<Gemini's supporting evidence with citations>

## Evidence Against / Nuances
<deepseek-r1 counter-evidence with CoT reasoning>

## Verdict
**[VERIFIED | PARTIALLY VERIFIED | UNVERIFIED | DISPUTED]**
Confidence: High / Medium / Low

## Citations
- [1] Author (Year). Title. Journal.
```

---

## 6. Core Framework Dependencies

| Module | Usage |
|:---|:---|
| `core.orchestration.pipeline_base.PipelineBase` | Phase class inheritance |
| `core.utils.atomic_writer.AtomicWriter` | Crash-safe report writes |
| `core.ai.llm_client.OllamaClient` | `deepseek-r1:8b` via `self.llm` |
| `playwright.async_api` | Gemini browser automation |

---

## 7. Key Invariants

1. **Sub-skill only**: Never route `gemini_verifier_agent` through `RouterAgent` directly.
2. **`self.llm` reuse**: Never instantiate `OllamaClient()` manually — always use `self.llm` inherited from `PipelineBase` (CODING_GUIDELINES §8.1).
3. **Structured logging only**: No bare `print()` — use `self.info()`, `self.error()`, `self.warning()` (CODING_GUIDELINES §8.1).
4. **Constructor integrity**: `super().__init__()` call in `PipelineBase` subclass must have matching parentheses — the unclosed parenthesis bug was fixed in ADR-018 (V9.17).
5. **3-round maximum**: Hard cap at 3 debate rounds. Do not make this configurable without profiling VRAM — each round is a full LLM context.
