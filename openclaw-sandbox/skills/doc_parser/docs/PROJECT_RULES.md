# PROJECT_RULES.md — Doc Parser Skill

> AI collaboration context for the `doc_parser` skill.
> Read this before making any code changes to this skill.

## Skill Summary

The doc_parser skill converts academic/technical PDF documents into structured Markdown knowledge bases through a 6-phase pipeline. It uses Docling for deep extraction, VLM for figure interpretation, and LLM-based Map-Reduce synthesis.

## Current State (2026-05-13)

- **Status**: Production — all phases implemented and integrated with `StateManager`
- **Models in use**: `llama3.2-vision` (P1d VLM); Docling (local) for P1a
- **Architecture version**: V4.0 (MarkItDown Office support, P0c, smart_highlighter delegation)

## Key Invariants

1. **Subject-based hierarchy**: `input/01_Inbox/<subject>/` → `output/02_Processed/<subject>/<pdf_id>/` → `output/05_Final_Knowledge/<subject>/<pdf_id>/`.
2. **IMMUTABLE P1a output**: `raw_extracted.md` is Docling's raw extraction. It is **never overwritten** after creation. All AI enrichment goes into `05_Final_Knowledge/`.
3. **Content-Loss Guard**: P3 validates `len(final) / len(raw) >= 0.30` before writing. If the ratio drops below 30%, the task is marked `❌` for human review. See DECISIONS.md for rationale.
4. **`checklist.md` is system-generated** — do not manually edit `data/doc_parser/state/checklist.md`.
5. **Zero-hardcoded prompts**: All LLM instructions live in `config/prompt.md`, parsed by `PipelineBase.get_prompt()`. Never embed prompts in Python code.
6. **Global config layer**: Hardware thresholds and Ollama runtime live in `core/config/global.yaml`, not in the skill's `config.yaml`.
7. **Office documents (P0c)**: `.pptx`, `.docx`, `.xlsx` enter via `Phase0cMarkItDown`; PDF-specific phases P0a/P1a/P1b/P1c/P1d are masked with `⏭️`. The P0c output mirrors the same interface as P1a.

## Architecture

```
Office (.pptx/.docx/.xlsx):
  P0c (MarkItDown) → P02 (smart_highlighter) → P03 (note_generator) → data/wiki/

PDF / Image (.pdf / .png):
  P00b (Security+PNG) → P00a (Diagnose) → P01a (Docling Extract)
                                              → P01b (Vector Charts)
                                              → P01c (OCR Gate)
                                              → P01d (VLM Vision)
  → P02 (smart_highlighter) → P03 (note_generator) → data/wiki/
```

Each phase is a class inheriting `core.PipelineBase`. Paths come from `config.yaml → PathBuilder → self.dirs[key]`.
PDF-specific phases are masked `⏭️` when processing Office documents (StateManager Office mask).

## File Locations

| Item | Path |
|:---|:---|
| Global config | `core/config/global.yaml` |
| Skill config | `skills/doc_parser/config/config.yaml` |
| LLM prompts | `skills/doc_parser/config/prompt.md` |
| Terminology list | `skills/doc_parser/config/priority_terms.json` |
| Security rules | `skills/doc_parser/config/security_policy.yaml` |
| Orchestrator | `skills/doc_parser/scripts/run_all.py` |
| Phase scripts | `skills/doc_parser/scripts/phases/p0*.py` |
| MarkItDown phase | `skills/doc_parser/scripts/phases/p00c_markitdown.py` |
| Architecture doc | `skills/doc_parser/docs/ARCHITECTURE.md` |

## Common Agent Tasks

**Adding PDFs**: Drop into `data/doc_parser/input/01_Inbox/<subject>/`, then run `python3 skills/doc_parser/scripts/run_all.py --process-all`.

**Process a single subject**: `python3 skills/doc_parser/scripts/run_all.py --process-all --subject AI_Papers`

**Interactive mode** (pause after VLM for human review): `python3 skills/doc_parser/scripts/run_all.py --process-all --interactive`

**Debugging a stuck phase**: Check `data/doc_parser/state/.pipeline_state.json` and `data/doc_parser/logs/system.log`.

**Switching models**: Edit `config.yaml` → relevant phase's `active_profile`, or run `python3 core/cli_config_wizard.py --skill doc_parser`.

## What NOT to Change Without Reading DECISIONS.md

- The `raw_extracted.md` immutability guarantee — it is the forensic baseline for all downstream AI processing
- Content-Loss Guard threshold (30%) — reducing it risks accepting severely truncated outputs
- Docling RAM limits in `config.yaml` (`pdf_processing.docling.max_ram_mb: 2560`) — heaviest single process
- P1c OCR confidence threshold — calibrated for Traditional Chinese + English mixed documents
- `core/config/global.yaml` hardware thresholds without cross-testing both skills
- P0c MarkItDown audio transcription — rejected by ADR (cloud API, no VAD, privacy risk)
