# DECISIONS.md — Audio Transcriber Skill

> Technical decision log. Every non-obvious architectural choice is recorded here
> with date, context, and rationale. Future developers must read the relevant entry
> before changing anything governed by that decision.

---

## 2026-04-16 — V7.1: Unified Core Architecture

**Decision**: Migrate all shared utilities (path resolution, state tracking, diff, daemon) from audio-transcriber-local code into `core/`.

**Context**: Voice-memo previously had its own `diff_tool.py`, `audit_tool.py`, a 329-line god-module `subject_manager.py`, and 10-line `Boundary-Safe Init` boilerplate repeated in every script.

**Chosen approach**:
- `core/bootstrap.py` — single `ensure_core_path(__file__)` call replaces all boilerplate
- `core/diff_engine.py` — generic `DiffEngine` + `AuditEngine` replace skill-local copies
- `core/state_manager.py` — generalised with `skill_name=` parameter; supports voice (`p1`–`p5`) and pdf (`p1a`–`p2b`) phase sets
- `skills/audio-transcriber/scripts/utils/subject_manager.py` — stripped to 3 CLI-interaction functions only

**Trade-off**: Slightly more indirection (everything goes through `core/`), but eliminates the drift problem where skill-local copies diverged from each other.

---

## 2026-04-16 — Config-Driven PathBuilder

**Decision**: Remove all `if skill_name == "audio-transcriber"` / `if skill_name == "doc-parser"` branches from `PathBuilder`. Instead, read `paths.phases` from each skill's `config.yaml`.

**Context**: Adding a third skill would have required editing `path_builder.py` which is a `core/` module — a clear violation of the open/closed principle.

**Chosen approach**: Each `config.yaml` now contains a `paths:` section with `phases:` subtree. `PathBuilder` reads it with `functools.cached_property` (lazy, cached after first access). Built-in `_DEFAULTS` dictionary provides fallback for any skill without a `paths:` block.

**Impact**: Adding a new skill requires ZERO changes to `core/`. Only `config.yaml` + phase scripts needed.

---

## 2026-04-15 — MLX Whisper over Faster-Whisper for Phase 1

**Decision**: Default to `mlx-community/whisper-large-v3-mlx` on Apple Silicon rather than `faster-whisper` medium.

**Context**: Initial testing on 16GB Apple Silicon M-series showed MLX Whisper at ~2.5× real-time speed vs Faster-Whisper's ~0.8× on MPS. Quality is identical (both use Whisper Large v3 weights).

**Chosen approach**: `config.yaml` `phase1.active_profile = apple_silicon_mps` uses MLX. A `default` profile with `faster-whisper` is kept as fallback for non-Apple or CUDA environments.

**Trade-off**: MLX model requires ~3GB disk space in `models/`; format is incompatible with non-MLX environments.

---

## 2026-04-14 — Verbatim Shield in Phase 2

**Decision**: Phase 2 proofreading adds a "Verbatim Shield" — the LLM is explicitly instructed not to add new content, only to correct transcription errors.

**Context**: Early testing showed `gemma3:12b` occasionally expanding sentences or adding unsupported facts when given freedom to "improve" the transcript. This is dangerous for academic notes.

**Chosen approach**: The P2 system prompt (in `config/prompt.md`) includes explicit constraints: correct typos → preserve meaning → never paraphrase → never add information not in the source.

**Trade-off**: Output may retain some awkward phrasing from the original speech. Accepted — accuracy over polish.

---

## 2026-04-14 — Hardware Safety Thresholds (16GB RAM)

**Decision**: RAM Warning = 800MB available, Critical = 400MB available; Temperature Warning = 85°C, Critical = 95°C.

**Context**: `gemma3:12b` in Ollama can consume up to 8GB VRAM/RAM at peak. On a 16GB machine, system overhead + Ollama + Python leaves ~3–4GB headroom. Pausing at 800MB prevents OOM kills.

**Chosen approach**: Thresholds embedded in `config.yaml` under `hardware.ram.*` and `hardware.temperature.*`. Not hardcoded — can be adjusted per machine without code changes.

**Note**: Temperature sensing is unavailable in some macOS kernel versions. The CPU usage proxy (≥98% triggers graceful stop) covers this case.

---

## 2026-04-12 — Phase 3: Map-Reduce over Single-Pass Synthesis

**Decision**: Phase 3 (merge) uses Map-Reduce: each chunk is independently refined, then all refined chunks are merged in a second pass.

**Context**: Single-pass synthesis over a full transcript (often 10,000+ tokens) exceeded `gemma3:12b`'s context window and produced severely truncated output.

**Chosen approach**: Chunk at `chunk_size=4000` characters, refine each independently, merge with a lightweight consolidation prompt. A `Content-Loss Guard` verifies the final output is ≥40% of the combined chunks.

**Trade-off**: 2× LLM calls vs single-pass. Accepted — correctness over speed.

---

## 2026-04-20 — V8.1: Triple-Layer Anti-Hallucination Defense

**Decision**: Implement a robust three-layer defense system in Phase 1 (`p01_transcribe.py`) to prevent Whisper's classic "hallucination loops" (repeating the same phrase infinitely) in high-noise/silence environments.

**Context**: Whisper often hallucinates when encountering long segments of silence or persistent background noise, looping text endlessly and ignoring subsequent speech.

**Chosen approach**:
1. **Layer 0 (Native Defense)**: Expose MLX-Whisper native parameters (`condition_on_previous_text=False`, `compression_ratio_threshold`, `no_speech_threshold`, `hallucination_silence_threshold`).
2. **Layer 1 (Pre-processing VAD)**: Use `pydub.silence` to aggressively strip silence before passing audio to Whisper. Added a `vad_max_removal_ratio` (default 90%) safety fallback — if VAD strips >90% of the audio, it's likely a false positive (threshold too aggressive), so it falls back to the original audio.
3. **Layer 2 (Post-processing Repetition Detection)**: Analyze each transcribed segment for n-gram repetition (e.g., repeating 4-grams) and zlib compression ratios. If a segment is flagged, perform a localized `retry_segment` with a slight temperature bump.

**Impact**: Effectively eliminates infinite loops in academic recordings with long pauses.

---

## 2026-04-20 — Multi-Clip Language Detection & Stderr Suppression

**Decision**: Upgrade language detection to sample 3 non-overlapping clips (start, middle, end) and use majority voting. Redirect subprocess stderr to `/dev/null` during `mlx_whisper.transcribe()`.

**Context**: 
1. If an audio file started with 30s of silence, Whisper would misidentify the language as English or Hebrew, causing the entire subsequent transcription to fail.
2. Every `mlx_whisper` subprocess execution triggered `MallocStackLogging` macOS system warnings, spamming the console.

**Chosen approach**:
1. `detect_audio_language` now divides the audio into 3 equal parts, takes a short clip from each, detects the language, and uses `collections.Counter` for majority voting. Can be bypassed entirely via `force_language` in `config.yaml` for a ~90s speedup per file.
2. Wraps `mlx_whisper.transcribe()` in `os.dup2` to redirect `fd 2` to `os.devnull`, cleanly suppressing OS-level `libmalloc` warnings without affecting Python exceptions.

**Trade-off**: Multi-clip detection adds overhead (3 separate Whisper invocations). Mitigated by offering the `force_language` config option for homogenous datasets.
