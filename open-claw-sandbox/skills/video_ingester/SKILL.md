# Video Ingester

A multimodal video processing pipeline designed for lecture recordings and seminars.

## Phases

- **Phase 1: Extract Keyframes (`p01_extract_keyframes.py`)**: Uses FFmpeg to extract high-quality JPEG screenshots from the video at regular intervals (default: every 30 seconds).
- **Phase 2: Transcribe Video (`p02_transcribe_video.py`)**: Uses MLX-Whisper with word-level timestamps to transcribe the audio track. The pipeline intelligently groups the spoken text into 30-second blocks, interleaving them with the corresponding keyframe screenshots.

## Output

The final Markdown note looks like an illustrated lecture transcript (`![slide.jpg]` followed by the transcript segment) and is automatically forwarded to the `note_generator` for summarization.

## Run Commands

```bash
cd open-claw-sandbox
python3 skills/video_ingester/scripts/run_all.py --process-all
```

## Config Pointers

- `config/config.yaml`: Sets Whisper model (`mlx-community/whisper-large-v3-turbo`) and `keyframe_interval_sec`.
