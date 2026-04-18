# CLAUDE.md — PDF Knowledge Skill

> AI collaboration context for the `pdf-knowledge` skill.
> Read this before making any code changes to this skill.

## Skill Summary

The pdf-knowledge skill converts academic/technical PDF documents into structured Markdown knowledge bases through a 6-phase pipeline. It uses Docling for deep extraction, VLM for figure interpretation, and LLM-based Map-Reduce synthesis.

## Current State (2026-04-16)

- **Status**: Production — all 6 phases implemented and integrated with `StateManager`
- **Models in use**: `llama3.2-vision` (P1d VLM), `qwen2.5:14b` (P3 synthesis); Docling (local) for P1a
- **Architecture version**: V3.0 (global config layer, zero-hardcoded prompts, subject hierarchy, IMMUTABLE principle)

## Key Invariants

1. **Subject-based hierarchy**: `input/01_Inbox/<subject>/` → `output/02_Processed/<subject>/<pdf_id>/` → `output/05_Final_Knowledge/<subject>/<pdf_id>/`.
2. **IMMUTABLE P1a output**: `raw_extracted.md` is Docling's raw extraction. It is **never overwritten** after creation. All AI enrichment goes into `05_Final_Knowledge/`.
3. **Content-Loss Guard**: P3 validates `len(final) / len(raw) ≥ 0.01` before writing. Threshold is intentionally low (1%) because dense academic texts compress naturally at high ratios.
4. **`checklist.md` is system-generated** — do not manually edit `data/pdf-knowledge/state/checklist.md`.
5. **Zero-hardcoded prompts**: All LLM instructions live in `config/prompt.md`, parsed by `PipelineBase.get_prompt()`. Never embed prompts in Python code.
6. **Global config layer**: Hardware thresholds and Ollama runtime live in `core/config/global.yaml`, not in the skill's `config.yaml`.

## Architecture

```
P0a (Diagnose) → P1a (Docling Extract) → P1b (Vector Charts) → P1c (OCR Gate)
                                                                       ↓
                                         P3 (Synthesis) ← P1d (VLM Vision)
```

Each phase is a class inheriting `core.PipelineBase`. Paths come from `config.yaml → PathBuilder → self.dirs[key]`.

## File Locations

| Item | Path |
|:---|:---|
| Global config | `core/config/global.yaml` |
| Skill config | `skills/pdf-knowledge/config/config.yaml` |
| LLM prompts | `skills/pdf-knowledge/config/prompt.md` |
| Terminology list | `skills/pdf-knowledge/config/priority_terms.json` |
| Security rules | `skills/pdf-knowledge/config/security_policy.yaml` |
| Orchestrator | `skills/pdf-knowledge/scripts/run_all.py` |
| Phase scripts | `skills/pdf-knowledge/scripts/phases/p0Na_*.py` |
| Architecture doc | `skills/pdf-knowledge/docs/ARCHITECTURE.md` |

## Common Agent Tasks

**Adding PDFs**: Drop into `data/pdf-knowledge/input/01_Inbox/<subject>/`, then run `python3 skills/pdf-knowledge/scripts/run_all.py --process-all`.

**Process a single subject**: `python3 skills/pdf-knowledge/scripts/run_all.py --process-all --subject AI_Papers`

**Interactive mode** (pause after VLM for human review): `python3 skills/pdf-knowledge/scripts/run_all.py --process-all --interactive`

**Debugging a stuck phase**: Check `data/pdf-knowledge/state/.pipeline_state.json` and `data/pdf-knowledge/logs/system.log`.

**Switching models**: Edit `config.yaml` → relevant phase's `active_profile`, or run `python3 core/cli_config_wizard.py --skill pdf-knowledge`.

## What NOT to Change Without Reading DECISIONS.md

- The `raw_extracted.md` immutability guarantee — it is the forensic baseline for all downstream AI processing
- Content-Loss Guard threshold (1%) — reducing it further risks accepting completely empty outputs
- Docling RAM limits in `config.yaml` (`pdf_processing.docling.max_ram_mb: 2560`) — heaviest single process
- P1c OCR confidence threshold — calibrated for Traditional Chinese + English mixed documents
- `core/config/global.yaml` hardware thresholds without cross-testing both skills
