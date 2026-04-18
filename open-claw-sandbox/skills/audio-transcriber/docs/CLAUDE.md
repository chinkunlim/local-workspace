# CLAUDE.md — Audio Transcriber Skill

> AI collaboration context for the `audio-transcriber` skill.
> Read this before making any code changes to this skill.

## Skill Summary

The audio-transcriber skill converts `.m4a` lecture recordings into Notion-ready structured knowledge documents through a 5-phase AI pipeline. It is the original and most mature skill in Open Claw.

## Current State (2026-04-16)

- **Status**: Production — all 5 phases working end-to-end
- **Model in use**: `gemma3:12b` (Ollama) for P0, P2, P3, P4, P5; MLX Whisper Large v3 for P1
- **Active subjects**: 助人歷程, 消費者心理學, 物理實驗, 環境與化學, 生理心理學, 社會心理學
- **Architecture version**: V7.1 (config-driven paths, `core/` bootstrap, OOP phases)

## Key Invariants

1. **Subject-based hierarchy**: `input/raw_data/<subject>/` and all output directories follow `<phase_dir>/<subject>/`.
2. **Phase sequential dependency**: P2 requires P1 ✅; P3 requires P2 ✅; etc. `StateManager` enforces this.
3. **Audio is never modified** — only read for transcription. All outputs are Markdown files.
4. **`checklist.md` is system-generated** — do not manually edit.

## Architecture

```
Phase 0 (Glossary) → Phase 1 (Whisper) → Phase 2 (Proofread) → Phase 3 (Merge) → Phase 4 (Highlight) → Phase 5 (Synthesis)
```

Each phase is a class inheriting `core.PipelineBase`. Paths come from `config.yaml → PathBuilder → self.dirs[key]`.

## File Locations

| Item | Path |
|:---|:---|
| Config | `skills/audio-transcriber/config/config.yaml` |
| LLM prompts | `skills/audio-transcriber/config/prompt.md` |
| Orchestrator | `skills/audio-transcriber/scripts/run_all.py` |
| Phase scripts | `skills/audio-transcriber/scripts/phases/p0N_*.py` |
| CLI helpers | `skills/audio-transcriber/scripts/utils/subject_manager.py` |
| Architecture doc | `skills/audio-transcriber/docs/ARCHITECTURE.md` |

## Common Agent Tasks

**Switching models**: Edit `config.yaml` → `phaseN.active_profile` or run `python3 core/cli_config_wizard.py --skill audio-transcriber`

**Adding a new subject**: Drop audio files into `data/audio-transcriber/input/raw_data/<subject>/`, then run `python3 skills/audio-transcriber/scripts/run_all.py --subject <subject>`.

**Debugging a stuck phase**: Check `data/audio-transcriber/state/.pipeline_state.json` and `data/audio-transcriber/logs/system.log`.

**Resetting a phase**: Delete the output file and re-run. `StateManager` detects the missing file and resets the task status.

## What NOT to Change Without Reading DECISIONS.md

- P2 chunking strategy (chunk_size and overlap are carefully tuned for 16GB RAM)
- The MLX Whisper model selection — MPS backend requires specific model format
- The Verbatim Shield logic in P2 — prevents LLM hallucination of new content
- Hardware thresholds in `config.yaml` — calibrated for Apple Silicon 16GB
