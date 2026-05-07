"""
run_all.py — Entry point for proofreader skill
"""

import os
import sys

# Internal Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from phases.p00_doc_proofread import Phase0DocProofread
from phases.p01_transcript_proofread import Phase1TranscriptProofread
from phases.p02_doc_completeness import Phase2DocCompleteness

from core import build_skill_parser


def main():
    parser = build_skill_parser("Proofreader Pipeline", include_force=True, include_subject=True)

    args = parser.parse_args()

    print("=" * 50)
    print("🚀 啟動 Proofreader Pipeline")
    print("=" * 50)

    Phase0DocProofread().run(force=args.force, subject=args.subject, file_filter=args.file)
    Phase1TranscriptProofread().run(force=args.force, subject=args.subject, file_filter=args.file)
    Phase2DocCompleteness().run(force=args.force, subject=args.subject, file_filter=args.file)

    print("=" * 50)
    print("🏁 Proofreader Pipeline 執行完畢")
    print("=" * 50)

    # Fire EventBus for RouterAgent
    from core.orchestration.event_bus import DomainEvent, EventBus

    # We don't have the exact filepath here if it processed many files.
    # The ideal way is to fire PipelineCompleted from within the phases for each file.
    # But for now, we just fire it generically if we know the subject.
    if args.subject:
        workspace_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        if args.file:
            filepath = os.path.join(
                workspace_root,
                "data",
                "proofreader",
                "output",
                "02_doc_completeness",
                args.subject,
                args.file,
            )
            EventBus.publish(
                DomainEvent(
                    name="PipelineCompleted",
                    source_skill="proofreader",
                    payload={"filepath": filepath, "subject": args.subject, "chain": []},
                )
            )


if __name__ == "__main__":
    main()
