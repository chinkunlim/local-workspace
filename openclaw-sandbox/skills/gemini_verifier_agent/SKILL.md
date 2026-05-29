---
name: gemini_verifier_agent
description: Cross-verifies claims via simulated dialogue with Gemini over Playwright.
metadata:
  openclaw:
    emoji: ♊️
    display_name: 內容驗證代理
state_tracking:
  phases:
  - p01_ai_debate
  labels:
    p01_ai_debate: P1 (Debate)
io_contracts:
  consumes:
  - text/markdown
  produces:
  - text/markdown
---

# Gemini Verifier Agent

> **Pipeline**: Claim Extraction → Evidence Search → AI Debate Verification → Report Generation

## Quick Start

```bash
# Run the verification agent on all pending claims
uv run skills/gemini_verifier_agent/scripts/run_all.py --process-all
```

## Anti-Hallucination Defense Architecture

| Phase | Script | Function |
|:---:|:---|:---|
| P1 | `p01_ai_debate.py` | Employs a multi-turn Socratic debate between local models and Gemini. **Hallucination guard**: forces strict citations from provided evidence only. |

## Global Standards

- **Browser Sandboxing**: Playwright instances are executed in isolated browser contexts with strict timeout policies.
- **Strict Parsing**: Debate outputs are parsed via constrained schema validation.
