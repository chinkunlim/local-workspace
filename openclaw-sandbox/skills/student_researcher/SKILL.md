---
name: student_researcher
description: Synthesizes final notes and applies APA format and Obsidian metadata.
metadata:
  openclaw:
    emoji: 🎓
    display_name: 研究員助手
state_tracking:
  phases:
  - p00_semantic_router
  - p01_claim_extraction
  - p02_synthesis
  labels:
    p00_semantic_router: P0 (Route)
    p01_claim_extraction: P1 (Extract)
    p02_synthesis: P2 (Synthesis)
io_contracts:
  consumes:
  - text/markdown
  produces:
  - text/markdown
---

# Student Researcher

> **Pipeline**: Claim Extraction → Synthesis → APA Formatting

## Quick Start

```bash
# Run the researcher agent
uv run skills/student_researcher/scripts/run_all.py --process-all
```

## Safety & Guardrails

| Phase | Function |
|:---:|:---|
| P0 | Semantic routing to determine research domain. |
| P1 | Claim Extraction strictly extracts factual assertions without generating new context. |
| P2 | Synthesis verifies citations against the established Knowledge Graph to prevent fabricated references. |

## Global Standards

- **Zero Temperature**: `config.yaml` enforces deterministic outputs to avoid reference fabrication.
- **Atomic Operations**: File writes use `AtomicWriter`.
