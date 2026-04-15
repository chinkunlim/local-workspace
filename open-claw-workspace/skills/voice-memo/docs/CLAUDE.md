# Voice Memo Operational Spec

Version: V7.3
Last Updated: 2026-04-15

## 1. Objective
Produce high-fidelity, reviewable academic notes from long-form audio with deterministic phase boundaries and strict output integrity.

## 2. Runtime Contract
- Executor: local Python
- LLM endpoint: runtime.ollama.api_url from config
- Config source: skills/voice-memo/config/config.yaml
- Prompt source: skills/voice-memo/config/prompt.md (or configured prompt path)

## 3. Phase Contract
1. P0: optional glossary drafting
2. P1: transcript generation
3. P2: transcript correction with context constraints
4. P3: segment merge and speaker formatting
5. P4: emphasis pass with anti-content-loss guard
6. P5: synthesis into study artifacts

## 4. Must-Not Rules
1. No silent fallback for missing required config.
2. No skipping checkpoint writes on pause/interrupt paths.
3. No direct hardcoded model values in code.
4. No mutation of previous phase outputs without explicit log trace.

## 5. Operator Interface
Primary CLI entry:
- skills/voice-memo/scripts/run_all.py

Key flags:
- --from
- --force
- --resume
- --interactive
- --subject

## 6. Verification Checklist
1. Preflight succeeds.
2. Phase logs emitted.
3. State file updated atomically.
4. Resume logic deterministic after interruption.
