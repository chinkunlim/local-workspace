from core.orchestration.skill_registry import SkillManifest


def _run(**kw):
    pass  # To be implemented when video_ingester runs


MANIFEST = SkillManifest(
    skill_name="video_ingester",
    description="Ingests lecture videos, extracts keyframes with FFmpeg, transcribes audio, and outputs interleaved Markdown.",
    phases=["p01_extract_keyframes", "p02_transcribe_video"],
    cli_entry="scripts/run_all.py",
    run_fn=_run,
    file_types=[".mp4", ".mov", ".mkv", ".webm"],
    tags=["video", "ffmpeg", "transcription"],
)
