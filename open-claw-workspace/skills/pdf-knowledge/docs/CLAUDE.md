# CLAUDE.md — PDF Knowledge Skill

> AI collaboration context for the `pdf-knowledge` skill.
> Read this before making any code changes to this skill.

## Skill Summary

The pdf-knowledge skill converts academic/technical PDF documents into structured Markdown knowledge bases through a 6-phase pipeline. It uses Docling for deep extraction, VLM for figure interpretation, and LLM-based Map-Reduce synthesis.

## Current State (2026-04-16)

- **Status**: Production — all 6 phases implemented and integrated with `StateManager`
- **Models in use**: `gemma3:12b` (Ollama) for P2a VLM and P2b synthesis; Docling (local) for P1b extraction
- **Architecture version**: V2.1 (config-driven paths, subject-based hierarchy, IMMUTABLE principle)

## Key Invariants

1. **Subject-based hierarchy**: `input/01_Inbox/<subject>/` → `output/02_Processed/<subject>/<pdf_id>/` → `output/05_Final_Knowledge/<subject>/<pdf_id>/`.
2. **IMMUTABLE P1b output**: `raw_extracted.md` is Docling's raw extraction. It is **never overwritten** after creation. All AI enrichment goes into `05_Final_Knowledge/`.
3. **Content-Loss Guard**: P2b validates that `len(final) / len(raw) ≥ 0.30` before writing. If ratio falls below threshold, synthesis is aborted to prevent LLM truncation.
4. **`checklist.md` is system-generated** — do not manually edit `data/pdf-knowledge/state/checklist.md`.

## Architecture

```
P1a (Diagnose) → P1b (Docling Extract) → P1c (Vector Charts) → P1d (OCR Gate)
                                                                       ↓
                                         P2b (Synthesis) ← P2a (VLM Vision)
```

Each phase is a class inheriting `core.PipelineBase`. Paths come from `config.yaml → PathBuilder → self.dirs[key]`.

## File Locations

| Item | Path |
|:---|:---|
| Config | `skills/pdf-knowledge/config/config.yaml` |
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
- Content-Loss Guard threshold (0.30) — reducing it risks silently accepting truncated knowledge bases
- Docling RAM limits in `config.yaml` (`pdf_processing.docling.max_ram_mb: 2560`) — Docling is the heaviest single process in the pipeline
- P1d OCR confidence threshold — calibrated for Traditional Chinese + English mixed documents
