# Feynman Simulator

This skill simulates the Feynman Technique by instantiating a multi-agent debate loop. It uses Playwright to bypass login walls, placing a Student Agent (local Ollama) against a Tutor Agent (Google Gemini).

## Phases

- **Phase 1: AI Debate (`p01_ai_debate.py`)**: A multi-turn Socratic debate. The Student proposes explanations, and the Tutor probes for weaknesses, blind spots, and logical inconsistencies.
- **Phase 2: Summarize (`p02_summarize.py`)**: Condenses the debate findings into a final refined document.

## Run Commands

```bash
cd open-claw-sandbox
python3 skills/feynman_simulator/scripts/run_all.py --process-all
```

## Config Pointers

- `config/config.yaml`: Sets model choices (e.g., `qwen2.5-coder:7b`) and debate rounds limit.
- Playwright persistent context is used for Gemini interaction.
