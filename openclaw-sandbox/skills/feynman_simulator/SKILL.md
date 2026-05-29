---
name: feynman_simulator
description: Simulates the Feynman Technique by instantiating a multi-agent debate
  loop with Playwright.
metadata:
  openclaw:
    emoji: 🧑‍🏫
    display_name: 費曼學習法模擬
state_tracking:
  phases:
  - p01_feynman_debate
  - p02_debate_synthesis
  labels:
    p01_feynman_debate: P1 (Debate)
    p02_debate_synthesis: P2 (Synthesis)
io_contracts:
  consumes:
  - text/markdown
  produces:
  - text/markdown
---

# Feynman Simulator

This skill simulates the Feynman Technique by instantiating a multi-agent debate loop. It uses Playwright to bypass login walls, placing a Student Agent (local Ollama) against a Tutor Agent (Google Gemini).

## Phases

- **Phase 1: AI Debate (`p01_ai_debate.py`)**: A multi-turn Socratic debate. The Student proposes explanations, and the Tutor probes for weaknesses, blind spots, and logical inconsistencies.
- **Phase 2: Summarize (`p02_summarize.py`)**: Condenses the debate findings into a final refined document.

## Run Commands

```bash
cd openclaw-sandbox
python3 skills/feynman_simulator/scripts/run_all.py --process-all
```

## Config Pointers

- `config/config.yaml`: Sets model choices — primary: `deepseek-r1:8b` (CoT reasoning for Socratic debate), fallback: `qwen3:8b`. Also configures debate rounds limit.
- Playwright persistent context is used for Gemini interaction.

## Safety & Hallucination Defenses

- The debate loop uses strict constraints to prevent LLMs from hallucinating external facts. All generated explanations must be grounded in the context.
