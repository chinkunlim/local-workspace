# Open Claw — Audio Transcriber Skill Architecture

> Version: V8.1 | Last Updated: 2026-05-01

## 1. Overview

The Audio Transcriber skill is Open Claw's voice-to-knowledge pipeline. It progressively converts `.m4a` audio lecture recordings into structured Obsidian-ready study notes.

```
data/raw/<subject>/lecture.m4a
          │
          ▼ P0: Glossary initialisation (terminology sync)
          │
          ▼ P1: MLX-Whisper transcription (V8.1 Triple-Layer Anti-Hallucination Defense)
            ├─ Layer 0: Native API guard (condition_on_previous_text=False)
            ├─ Layer 1: VAD pre-processing (pydub silence trimming + removal rate safety valve)
            ├─ Language detection: multi-clip majority-vote (overridable via force_language)
            └─ Layer 2: Local retry (N-gram / zlib repetition detection)
          │
data/audio-transcriber/output/01_transcript/<subject>/lecture.md
          │
          ▼ P2: LLM proofreading + glossary term protection
data/audio-transcriber/output/02_proofread/<subject>/lecture.md
          │
          ▼ P3: Cross-segment merge and refinement
data/audio-transcriber/output/03_merged/<subject>/lecture.md
          │
          ▼ P4: Highlight annotations (delegated to smart_highlighter)
          ▼ P5: Synthesis (delegated to note_generator → data/wiki/)
```

---

## 2. Directory Structure

```
skills/audio-transcriber/
├── SKILL.md                    # Quick-start guide
├── config/
│   ├── config.yaml             # All models, paths, thresholds
│   └── prompt.md               # Phase 2–3 LLM instruction templates
├── docs/
│   ├── ARCHITECTURE.md         # This file
│   ├── DECISIONS.md            # Architectural decision log (ADR format)
│   └── CLAUDE.md               # AI collaboration context
└── scripts/
    ├── run_all.py              # Orchestrator — interactive 5-phase executor
    ├── phases/
    │   ├── p00_glossary.py     # Phase 0: Glossary initialisation
    │   ├── p01_transcribe.py   # Phase 1: Audio transcription (MLX-Whisper)
    │   ├── p02_proofread.py    # Phase 2: LLM intelligent proofreading
    │   └── p03_merge.py        # Phase 3: Cross-segment merge and refinement
    └── utils/
        └── subject_manager.py  # Audio-specific CLI interaction helpers
```

---

## 3. Core Architecture — Anti-Hallucination Mechanism (V8.1)

### 3.0 Triple-Layer Anti-Hallucination Defense

Designed to counter the "Infinite Repetition Loop (Hallucination Loop)" that Whisper produces under high-noise or long-silence conditions.

1. **Layer 0 (Native API)**: Enables `condition_on_previous_text=False` and `hallucination_silence_threshold` — built-in MLX-Whisper defence parameters.
2. **Layer 1 (Input — VAD)**: Uses `pydub.silence` to pre-trim silence before transcription. A `vad_max_removal_ratio` safety valve (default: 90%) is enforced; if the removal ratio exceeds this threshold, the system falls back to the original raw audio to prevent over-trimming.
3. **Layer 2 (Post-processing — Repetition Detection)**: Scans generated segments using N-gram and zlib compression ratio analysis. If a hallucination loop is detected, the affected segment is automatically retried with a higher temperature (`retry_segment`).
4. **Language Detection**: Uses a "first-middle-last 3-clip majority-vote" strategy to prevent single-clip silence from causing language misidentification (overridable in `config.yaml` via `force_language` to speed up processing).

### 3.1 Inheritance Chain

Every Phase class inherits from `core.orchestration.pipeline_base.PipelineBase`:

```python
from core.utils.bootstrap import ensure_core_path
ensure_core_path(__file__)

from core.orchestration.pipeline_base import PipelineBase

class Phase2Proofread(PipelineBase):
    def __init__(self) -> None:
        super().__init__(phase_key="p2", phase_name="Proofreading")
        # self.dirs["p2"] → data/audio-transcriber/output/02_proofread (from config.yaml)
        # self.llm        → OllamaClient (auto-configured)
        # self.state_manager → StateManager (auto-configured)
```

### 3.2 Config-Driven Path Resolution

All paths come from `config.yaml`'s `paths:` section. No hardcoded paths anywhere:

```yaml
# skills/audio-transcriber/config/config.yaml
paths:
  input:  "input/raw_data"
  output: "output"
  state:  "state"
  logs:   "logs"
  phases:
    p0: "input/raw_data"
    p1: "output/01_transcript"
    p2: "output/02_proofread"
    p3: "output/03_merged"
```

### 3.3 State Tracking

- `core.state.state_manager.StateManager` manages `data/audio-transcriber/state/.pipeline_state.json`
- Each phase writes a ✅ status automatically upon completion
- SHA-256 hash changes in output `.md` files trigger a DAG cascade reset
- `data/audio-transcriber/state/checklist.md` is auto-generated as a human-readable progress tracker

### 3.4 Checkpoint Resume

- `run_all.py` supports graceful shutdown on first `Ctrl+C`, and force-kill on second
- Pause position is saved via `core.state.state_manager.StateManager.save_checkpoint()`
- `--resume` flag automatically continues from the last interrupted point

---

## 4. Data Flow

```
data/raw/<subject>/         ──(Watchdog)──►  InboxDaemon
                                                  │
                                           Triggers run_all.py
                                                  │
                                   ┌──────────────┼──────────────┐
                                  P0             P1             P2
                             (Glossary)     (Transcribe)   (Proofread)
                                                  │
                                                  P3
                                               (Merge)
                                                  │
                                    data/audio-transcriber/output/03_merged/
```

---

## 5. Core Framework Dependencies

| Core Module | Usage in Audio Transcriber |
|:---|:---|
| `core.orchestration.pipeline_base.PipelineBase` | Base class for all Phase classes |
| `core.state.state_manager.StateManager` | P1–P3 progress tracking |
| `core.utils.path_builder.PathBuilder` | Resolves directories from `config.yaml` |
| `core.ai.llm_client.OllamaClient` | P2–P3 LLM inference |
| `core.utils.glossary_manager.GlossaryManager` | Glossary sync with doc-parser |
| `core.services.inbox_daemon.SystemInboxDaemon` | Watches `data/raw/` for new audio files |

---

## 6. CLI Usage

```bash
cd open-claw-sandbox

# Run full pipeline on all pending files
python3 skills/audio-transcriber/scripts/run_all.py --process-all

# Process a specific subject only
python3 skills/audio-transcriber/scripts/run_all.py --subject YourSubject

# Force full re-run
python3 skills/audio-transcriber/scripts/run_all.py --process-all --force

# Resume from checkpoint
python3 skills/audio-transcriber/scripts/run_all.py --resume

# Regenerate glossary only
python3 skills/audio-transcriber/scripts/run_all.py --glossary

# Switch LLM model profile interactively
python3 core/cli/cli_config_wizard.py --skill audio-transcriber
```

---

## 7. Model Profile Switching

`config.yaml` uses an `active_profile` mechanism:

```yaml
phase2:
  active_profile: strict_gemma
  profiles:
    strict_gemma:
      model: gemma3:12b
      chunk_size: 3000
    fast_draft:
      model: gemma3:4b
      chunk_size: 5000
```

Call `python3 core/cli/cli_config_wizard.py --skill audio-transcriber` to switch profiles interactively.
