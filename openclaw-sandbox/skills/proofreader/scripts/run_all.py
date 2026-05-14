"""
run_all.py — Orchestrator for Proofreader Pipeline
==================================================
Standardized PipelineBase orchestrator for Proofreader.
Supports interactive menu, DAG tracking, resume checkpoints, and standard handoff.
"""

import os
import sys

# Internal Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from phases.p01_doc_proofread import Phase1DocProofread
from phases.p02_transcript_proofread import Phase2TranscriptProofread
from phases.p03_doc_completeness import Phase3DocCompleteness

from core import (
    PipelineBase,
    SessionState,
    StateManager,
    build_skill_parser,
)


class ProofreaderOrchestrator(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="orchestrator",
            phase_name="Proofreader 管線協調器",
            skill_name="proofreader",
        )
        self._state_manager = StateManager(self.base_dir, skill_name="proofreader")

    def _populate_state_from_sources(self, subject_filter: str = None):
        """Scan both source directories and inject any found files into StateManager.state.

        Persists to JSON so subsequent Phase instances (each with a fresh StateManager)
        can read the pre-populated entries from disk.
        """
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

        # Source 1: doc_parser output (3-level: {subject}/{pdf_id}/{pdf_id}_raw_extracted.md)
        doc_parser_dir = os.path.join(
            workspace_root, "data", "doc_parser", "output", "01_processed"
        )
        # Source 2: audio_transcriber merged output (2-level: {subject}/{fname}.md)
        audio_dir = os.path.join(workspace_root, "data", "audio_transcriber", "output", "03_merged")

        with self._state_manager._lock:
            for source_dir, three_level in [(doc_parser_dir, True), (audio_dir, False)]:
                if not os.path.exists(source_dir):
                    continue

                subjects = (
                    [subject_filter]
                    if subject_filter
                    else [
                        d
                        for d in os.listdir(source_dir)
                        if os.path.isdir(os.path.join(source_dir, d))
                    ]
                )

                for subj in subjects:
                    subj_dir = os.path.join(source_dir, subj)
                    if not os.path.isdir(subj_dir):
                        continue

                    if subj not in self._state_manager.state:
                        self._state_manager.state[subj] = {}

                    if three_level:
                        # doc_parser: {subj_dir}/{pdf_id}/ directories
                        for pdf_id in os.listdir(subj_dir):
                            pdf_dir = os.path.join(subj_dir, pdf_id)
                            if not os.path.isdir(pdf_dir):
                                continue
                            raw_md = os.path.join(pdf_dir, f"{pdf_id}_raw_extracted.md")
                            sanitized_md = os.path.join(pdf_dir, "sanitized.md")
                            if not os.path.exists(raw_md) and not os.path.exists(sanitized_md):
                                continue

                            target_md = sanitized_md if os.path.exists(sanitized_md) else raw_md
                            fhash = self._state_manager.get_file_hash(target_md)
                            fname = f"{pdf_id}.md"

                            if fname not in self._state_manager.state[subj]:
                                self._state_manager.state[subj][fname] = {
                                    **dict.fromkeys(self._state_manager.PHASES, "⏳"),
                                    "p2": "⏭️",
                                    "p3": "⏭️",  # Doc files skip P2 and P3
                                    "hash": fhash,
                                    "date": "",
                                    "note": "",
                                    "output_hashes": {},
                                    "char_count": {},
                                }
                            else:
                                if self._state_manager.state[subj][fname].get("hash") != fhash:
                                    self._state_manager.state[subj][fname]["hash"] = fhash
                                    self._state_manager.state[subj][fname]["p1"] = "⏳"
                                    self._state_manager.state[subj][fname]["note"] = "來源檔更新"
                                if self._state_manager.state[subj][fname].get("p2") != "⏭️":
                                    self._state_manager.state[subj][fname]["p2"] = "⏭️"
                                if self._state_manager.state[subj][fname].get("p3") != "⏭️":
                                    self._state_manager.state[subj][fname]["p3"] = "⏭️"
                    else:
                        # audio_transcriber: flat *.md files in subj_dir
                        for fname in os.listdir(subj_dir):
                            if not fname.endswith(".md") or fname == "correction_log.md":
                                continue

                            fhash = self._state_manager.get_file_hash(os.path.join(subj_dir, fname))

                            if fname not in self._state_manager.state[subj]:
                                self._state_manager.state[subj][fname] = {
                                    **dict.fromkeys(self._state_manager.PHASES, "⏳"),
                                    "p1": "⏭️",  # Audio files skip P1
                                    "hash": fhash,
                                    "date": "",
                                    "note": "",
                                    "output_hashes": {},
                                    "char_count": {},
                                }
                            else:
                                if self._state_manager.state[subj][fname].get("hash") != fhash:
                                    self._state_manager.state[subj][fname]["hash"] = fhash
                                    self._state_manager.state[subj][fname]["p2"] = "⏳"
                                    self._state_manager.state[subj][fname]["p3"] = "⏳"
                                    self._state_manager.state[subj][fname]["note"] = "來源檔更新"
                                if self._state_manager.state[subj][fname].get("p1") != "⏭️":
                                    self._state_manager.state[subj][fname]["p1"] = "⏭️"

            # Persist to JSON so fresh Phase StateManager instances can read it
            self._state_manager._save_state()

    def run(self, args):
        subject_filter = getattr(args, "subject", None)
        self._populate_state_from_sources(subject_filter)

        # Checkpoint resume detection
        resume_from = None
        if args.resume:
            resume_from = self._state_manager.load_checkpoint()
            if resume_from:
                print(
                    f"➩️  [強制斷點續傳] {resume_from.get('subject')} / "
                    f"{resume_from.get('filename')} @ "
                    f"{resume_from.get('phase_key', '').upper()}"
                )
            else:
                print("❗  --resume 指定但尚無 Checkpoint，將從頭開始。")
        elif not args.force:
            resume_from = self.prompt_checkpoint_resume()

        self._state_manager.print_dashboard()

        phases = [Phase1DocProofread, Phase2TranscriptProofread, Phase3DocCompleteness]

        PipelineBase.run_skill_pipeline(
            phases=phases,
            args=args,
            start_phase=getattr(args, "start_phase", 1),
            resume_from=resume_from,
            print_dashboard_between=True,
        )

        # Check pending files and optionally start dashboard
        self._check_dashboard_pending()

    def _check_dashboard_pending(self):
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        out_dir = os.path.join(workspace_root, "data", "proofreader", "output")
        verified_dir = os.path.join(out_dir, "04_final_verified")

        pending_count = 0
        phases = ["01_doc_proofread", "02_transcript_proofread", "03_doc_completeness"]
        for phase in phases:
            phase_dir = os.path.join(out_dir, phase)
            if not os.path.exists(phase_dir):
                continue
            for subj in os.listdir(phase_dir):
                subj_dir = os.path.join(phase_dir, subj)
                if not os.path.isdir(subj_dir):
                    continue
                for fname in os.listdir(subj_dir):
                    if not fname.endswith(".md") or fname == "correction_log.md":
                        continue
                    verified_path = os.path.join(verified_dir, subj, fname)
                    if not os.path.exists(verified_path):
                        pending_count += 1

        print("\n" + "=" * 50)
        if pending_count > 0:
            print(f"📊 總結：目前共有 {pending_count} 份文件等待人工核對與合併。")
            try:
                choice = input("👉 是否要立即開啟 Dashboard 網頁進行核對？(y/N): ").strip().lower()
                if choice == "y":
                    print(
                        "🚀 啟動 Dashboard (http://localhost:5000) ... 於終端機按 Ctrl+C 可結束伺服器。"
                    )
                    import subprocess

                    subprocess.run(
                        [sys.executable, os.path.join(os.path.dirname(__file__), "dashboard.py")]
                    )
            except KeyboardInterrupt:
                print("\n已取消啟動。")
        else:
            print(
                "✨ 總結：目前【沒有】需要人工核查的文件，所有產出皆已驗證 (位於 04_final_verified)！"
            )
        print("=" * 50 + "\n")


def main():
    parser = build_skill_parser(
        "Proofreader Pipeline",
        include_force=True,
        include_subject=True,
        include_resume=True,
        include_interactive=True,
        include_start_phase=True,
    )
    args = parser.parse_args()

    # The outer try/except is a last-resort safety net for interrupts that happen outside
    # a running phase. Inside phases, PipelineBase._setup_signals() handles it.
    try:
        ProofreaderOrchestrator().run(args)
    except KeyboardInterrupt:
        print("\n\n⏸️  已收到 Ctrl+C（在管線外部），直接離開。")
        PipelineBase.notify_os("執行已中斷")
        sys.exit(130)


if __name__ == "__main__":
    main()
