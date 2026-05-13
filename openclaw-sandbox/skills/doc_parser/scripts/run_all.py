"""
run_all.py — Orchestrator for Doc Parser Pipeline
==================================================
Standardized PipelineBase orchestrator for doc_parser.
Replaces the legacy QueueManager with horizontal Phase execution.
"""

import os
import sys

# Internal Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from phases.p00a_diagnostic import Phase0aDiagnostic
from phases.p00b_png_pipeline import Phase0bPNGPipeline
from phases.p01a_engine import Phase1aPDFEngine
from phases.p01b_text_sanitizer import Phase1bTextSanitizer
from phases.p01b_vector_charts import Phase1bVectorChartExtractor
from phases.p01c_ocr_gate import Phase1cOCRQualityGate
from phases.p01d_vlm_vision import Phase1dVLMVision

from core import (
    PipelineBase,
    StateManager,
    build_skill_parser,
)


class DocParserOrchestrator(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="orchestrator",
            phase_name="Doc Parser 管線協調器",
            skill_name="doc_parser",
        )
        self._state_manager = StateManager(self.base_dir, skill_name="doc_parser")

    def startup_check(self) -> bool:
        """
        Preflight checks before starting the pipeline:
        1. Chrome Profile path confirmation (config check)
        2. poppler-utils availability
        3. System health baseline
        """
        print("=" * 50)
        print("✈️  進行啟動前置檢查 (Preflight Check)...")

        # 1. Ensure directories exist
        os.makedirs(self.dirs["inbox"], exist_ok=True)
        for d in self.dirs.values():
            os.makedirs(d, exist_ok=True)

        # 2. Check poppler-utils
        import subprocess

        try:
            subprocess.run(["pdfinfo", "-v"], capture_output=True, timeout=5)
        except FileNotFoundError:
            self.error("❌ poppler-utils 未安裝！請執行: brew install poppler")
            return False

        # 3. System health baseline
        if self.check_system_health():
            self.error("❌ 系統資源不足，請稍後再試")
            return False

        print("✅ 前置檢查通過。\n")
        return True

    def run(self, args) -> None:
        if not self.startup_check():
            sys.exit(1)

        # Populate state from physical files in inbox/
        self._state_manager.sync_physical_files()

        # Mask phases based on file type
        with self._state_manager._lock:
            for subj, files in self._state_manager.state.items():
                if subj == "_simple_":
                    continue
                for fname, record in files.items():
                    ext = os.path.splitext(fname)[1].lower()
                    if ext == ".pdf":
                        if record.get("p0b") != "⏭️":
                            record["p0b"] = "⏭️"
                    elif ext in [".png", ".jpg", ".jpeg"]:
                        for p in ["p0a", "p1a", "p1b_s", "p1b", "p1c", "p1d"]:
                            if record.get(p) != "⏭️":
                                record[p] = "⏭️"
            self._state_manager._save_state()

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

        # Register all horizontal phases
        phases = [
            Phase0bPNGPipeline,  # phase0b_png
            Phase0aDiagnostic,  # phase0a
            Phase1aPDFEngine,  # phase1a
            Phase1bTextSanitizer,  # phase1b_sanitizer
            Phase1bVectorChartExtractor,  # phase1b
            Phase1cOCRQualityGate,  # phase1c
            Phase1dVLMVision,  # phase1d
        ]

        PipelineBase.run_skill_pipeline(
            phases=phases,
            args=args,
            start_phase=getattr(args, "start_phase", 1),
            resume_from=resume_from,
            print_dashboard_between=True,
        )


def main():
    parser = build_skill_parser(
        "Doc Parser Pipeline",
        include_force=True,
        include_subject=True,
        include_resume=True,
        include_interactive=True,
        include_start_phase=True,
    )
    args = parser.parse_args()

    orchestrator = DocParserOrchestrator()
    orchestrator.run(args)


if __name__ == "__main__":
    main()
