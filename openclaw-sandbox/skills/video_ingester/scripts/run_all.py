import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

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
    args = parser.parse_args()

    PipelineBase.run_skill_pipeline(phases, args)


if __name__ == "__main__":
    main()
