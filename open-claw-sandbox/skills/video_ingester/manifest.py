from core.models.manifest import SkillManifest


def get_manifest() -> SkillManifest:
    return SkillManifest(
        name="video_ingester",
        description="Ingests lecture videos, extracts keyframes with FFmpeg, transcribes audio, and outputs interleaved Markdown.",
        version="1.0.0",
        author="Open Claw",
        phases=[
            {
                "name": "p01_extract_keyframes",
                "description": "Extracts keyframes from video at regular intervals using FFmpeg.",
            },
            {
                "name": "p02_transcribe_video",
                "description": "Transcribes audio track using MLX-Whisper and interleaves keyframes.",
            },
        ],
    )
