import os
import sys

from core.orchestration.pipeline_base import PipelineBase
from skills.video_ingester.scripts.phases.p01_extract_keyframes import Phase1ExtractKeyframes
from skills.video_ingester.scripts.phases.p02_transcribe_video import Phase2TranscribeVideo


def main():
    phases = [
        Phase1ExtractKeyframes,
        Phase2TranscribeVideo,
    ]

    import argparse

    parser = argparse.ArgumentParser(description="Video Ingester Pipeline")
    parser.add_argument("--process-all", action="store_true", help="Run without prompts")
    parser.add_argument("--subject", type=str, help="Filter by subject folder")
    parser.add_argument("--single", action="store_true", help="Stop after first file")
    parser.add_argument("--clear", "-c", action="store_true", help="清除此 skill 的所有進度記錄")
    args = parser.parse_args()

    PipelineBase.run_skill_pipeline(phases, args)


if __name__ == "__main__":
    main()
