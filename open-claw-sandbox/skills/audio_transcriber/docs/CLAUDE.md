# CLAUDE.md — Audio Transcriber Skill

> AI collaboration context for the `audio_transcriber` skill.
> Read this before making any code changes to this skill.

## Skill Summary

The audio_transcriber skill converts `.m4a` lecture recordings into Obsidian-ready structured knowledge documents through a 5-phase AI pipeline. It is the original and most mature skill in Open Claw.

## Current State (2026-05-01)

- **Status**: Production — all 5 phases working end-to-end
- **Model in use**: `gemma3:12b` (Ollama) for P0, P2, P3; MLX-Whisper Large v3 for P1; delegated to `smart_highlighter` for P4; delegated to `note_generator` for P5
- **Architecture version**: V8.1 (anti-hallucination triple-layer defense)

## Key Invariants

1. **Subject-based hierarchy**: `data/raw/<subject>/` and all output directories follow `<phase_dir>/<subject>/`.
2. **Phase sequential dependency**: P2 requires P1 ✅; P3 requires P2 ✅; etc. `StateManager` enforces this.
3. **Audio files are never modified** — only read for transcription. All outputs are Markdown files.
4. **`checklist.md` is system-generated** — do not manually edit.
5. **Core imports must use sub-package paths** — see `CODING_GUIDELINES.md §3.1`.

## Architecture

```
Phase 0 (Glossary) → Phase 1 (MLX-Whisper) → Phase 2 (Proofread) → Phase 3 (Merge) → Phase 4 (Highlight) → Phase 5 (Synthesis)
```

Each phase is a class inheriting `core.orchestration.pipeline_base.PipelineBase`. Paths come from `config.yaml → PathBuilder → self.dirs[key]`.

## File Locations

| Item | Path |
|:---|:---|
| Config | `skills/audio_transcriber/config/config.yaml` |
| LLM prompts | `skills/audio_transcriber/config/prompt.md` |
| Orchestrator | `skills/audio_transcriber/scripts/run_all.py` |
| Phase scripts | `skills/audio_transcriber/scripts/phases/p0N_*.py` |
| CLI helpers | `skills/audio_transcriber/scripts/utils/subject_manager.py` |
| Architecture doc | `skills/audio_transcriber/docs/ARCHITECTURE.md` |

## Common Agent Tasks

**Switching models**: Edit `config.yaml` → `phaseN.active_profile` or run `python3 core/cli/cli_config_wizard.py --skill audio_transcriber`

**Adding a new subject**: Drop audio files into `data/raw/<subject>/`. The inbox daemon routes them automatically.

**Debugging a stuck phase**: Check `data/audio_transcriber/state/.pipeline_state.json` and `data/audio_transcriber/logs/system.log`.

**Resetting a phase**: Delete the output file and re-run. `StateManager` detects the missing file and resets the task status.

## What NOT to Change Without Reading DECISIONS.md

- P2 chunking strategy (chunk_size and overlap are carefully tuned for 16 GB RAM)
- The MLX-Whisper model selection — MPS backend requires specific model format
- The VAD safety valve (`vad_max_removal_ratio`) — calibrated to prevent over-trimming
- Hardware thresholds in `config.yaml` — calibrated for Apple Silicon 16 GB
