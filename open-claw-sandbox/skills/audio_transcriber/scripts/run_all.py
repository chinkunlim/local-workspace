"""
run_all.py — Audio Transcriber Skill Orchestrator (V8.0)
==================================================
Full 5-Phase Pipeline Runner (+ Phase 0 Glossary).
Refactored to VoiceMemoOrchestrator(PipelineBase) architecture —
symmetrical with QueueManager in doc_parser.

V8.0 Changes (vs V7.0):
- Wrapped all orchestration logic in VoiceMemoOrchestrator(PipelineBase)
- Removed hardcoded global base_dir and duplicate _runtime_config
- StateManager now explicitly declares skill_name="audio_transcriber"
- SessionState persisted at RUNNING / PAUSED / STOPPED / COMPLETED transitions
- startup_check() method replaces bare preflight_check() function
- Standard core.bootstrap (no repeated sys/os import block)
"""

# Group 1 — stdlib
import os
import sys

# Group 2 — Internal Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

# Group 3 — Core imports
from phases.p00_glossary import Phase0Glossary
from phases.p01_transcribe import Phase1Transcribe
from phases.p02_glossary_apply import Phase2GlossaryApply
from phases.p03_merge import Phase3Merge

from core import (
    PipelineBase,
    SessionState,
    StateManager,
    build_skill_parser,
)

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class VoiceMemoOrchestrator(PipelineBase):
    """Full audio_transcriber pipeline orchestrator.

    Manages Phase 0–5 in sequence, with checkpoint resume,
    graceful pause/stop, and SessionState persistence.
    Symmetrical to doc_parser's QueueManager.
    """

    def __init__(self) -> None:
        super().__init__(
            phase_key="orchestrator",
            phase_name="Audio Transcriber 管線協調器",
            skill_name="audio_transcriber",
        )
        self._state_manager = StateManager(self.base_dir, skill_name="audio_transcriber")

    # ------------------------------------------------------------------ #
    #  Startup                                                             #
    # ------------------------------------------------------------------ #

    def startup_check(self) -> bool:
        """Preflight checks before starting the pipeline.

        Validates:
        1. Input .m4a files exist in data/audio_transcriber/input/
        2. Ollama is reachable
        3. Required Python packages are installed

        Returns:
            True if safe to proceed, False if any check failed.
        """
        import requests

        print("=" * 50)
        print("✈️  進行啟動前置檢查 (Preflight Check)...")
        fail = False

        # 1. Check input audio files
        input_dir = os.path.join(self.base_dir, "input")
        if not os.path.exists(input_dir) or not any(
            f.endswith(".m4a") for _, _, fl in os.walk(input_dir) for f in fl
        ):
            print("❌ 錯誤：找不到任何 .m4a 來源。")
            fail = True

        # 2. Check Ollama connectivity (read from self.config_manager — no duplication)
        try:
            ollama_cfg = self.config_manager.get_section("runtime", {}).get("ollama", {})
            api_url = ollama_cfg.get("api_url")
            if not api_url:
                raise RuntimeError("audio_transcriber runtime.ollama.api_url is missing")
            tags_url = api_url.replace("/api/generate", "/api/tags")
            requests.get(tags_url, timeout=3).raise_for_status()
        except Exception:
            print("❌ 錯誤：無法連線至 Ollama (`ollama serve`)。")
            fail = True

        # 3. Check required packages
        try:
            import mlx_whisper  # noqa: F401
            import pypdf
            import tqdm
        except ImportError as exc:
            print(f"❌ 錯誤：缺少必要套件 {exc.name}")
            fail = True

        if fail:
            return False

        print("✅ 前置檢查通過。")
        return True

    # ------------------------------------------------------------------ #
    #  Checkpoint Resume                                                   #
    # ------------------------------------------------------------------ #

    def _check_and_resume(self) -> dict | None:
        """Prompt the user to resume from a saved checkpoint (if any).

        Returns:
            The checkpoint dict to resume from, or None to start fresh.
        """
        cp = self._state_manager.load_checkpoint()
        if not cp:
            return None

        saved_at = cp.get("saved_at", "不明")
        print("\n" + "═" * 56)
        print("📌 偵測到上次暫停的斷點 (Checkpoint)")
        print(f"   時間：{saved_at}")
        print(f"   科目：{cp.get('subject', '?')}")
        print(f"   檔案：{cp.get('filename', '?')}")
        print(f"   Phase：{cp.get('phase_key', '?').upper()}")
        print("═" * 56)
        print("請選擇：")
        print("  [C] Continue — 從上次斷點繼續")
        print("  [N] New       — 全新開始（清除 Checkpoint）")

        try:
            choice = input("請輸入 (C/N) [Enter = C]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n已選擇全新開始。")
            self._state_manager.clear_checkpoint()
            return None

        if choice == "n":
            self._state_manager.clear_checkpoint()
            print("🗑️  Checkpoint 已清除，全新開始。")
            return None

        print("➩️  從斷點繼續。")
        return cp

    # ------------------------------------------------------------------ #
    #  Main Orchestration                                                  #
    # ------------------------------------------------------------------ #

    def run(self, args) -> None:
        """Execute the full audio_transcriber pipeline based on parsed CLI args.

        Args:
            args: Parsed argparse Namespace from build_skill_parser().
        """
        if not self.startup_check():
            sys.exit(1)

        self._state_manager.sync_physical_files()

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
            resume_from = self._check_and_resume()

        self._state_manager.print_dashboard()

        # Optional glossary generation
        if args.glossary:
            print("\n" + "=" * 50)
            print("📚 Phase 0: 詞庫自動生成...")
            print("=" * 50)
            Phase0Glossary().run(
                force=args.glossary_force,
                merge=args.glossary_merge,
                subject=args.subject,
            )

        phases_classes = {
            1: Phase1Transcribe,
            2: Phase2GlossaryApply,
            3: Phase3Merge,
        }

        completed_normally = False
        any_stopped = False
        try:
            for p_num in range(args.start_phase, 4):
                if p_num not in phases_classes:
                    continue
                print(f"\n{'=' * 50}")
                print(f"🚀 開始執行 Phase {p_num}...")
                print(f"{'=' * 50}")

                p_obj = phases_classes[p_num]()
                if p_obj.stop_requested:
                    any_stopped = True
                    break

                # Pass checkpoint only to the matching phase
                phase_resume = None
                if resume_from:
                    if resume_from.get("phase_key", "") == p_obj.phase_key:
                        phase_resume = resume_from
                    # Earlier checkpoint phase → this phase runs in full

                p_obj.run(
                    force=args.force,
                    subject=args.subject,
                    file_filter=args.file,
                    single_mode=args.single,
                    resume_from=phase_resume,
                )

                # Clear resume_from after first use to avoid contaminating later phases
                resume_from = None

                if p_obj.stop_requested:
                    if p_obj.pause_requested:
                        self._write_session_state(SessionState.PAUSED)
                        print("💾 Pipeline 已暫停並儲存進度，下次執行自動從斷點繼續。")
                    else:
                        self._write_session_state(SessionState.STOPPED)
                        self._state_manager.clear_checkpoint()
                        print("🛑 Pipeline 已停止（不儲存進度）。")
                    break

                # Reload state for dashboard (other phases may have mutated it)
                self._state_manager = StateManager(self.base_dir, skill_name="audio_transcriber")
                self._state_manager.print_dashboard()

                if args.interactive and p_num < 3:
                    if sys.stdin.isatty():
                        print(f"✋ Phase {p_num} 已完成。請按 [Enter] 繼續...")
                        input()
            else:
                # for-loop completed without break
                completed_normally = True

        except SystemExit:
            pass
        except KeyboardInterrupt:
            self._write_session_state(SessionState.STOPPED, context={"error": "KeyboardInterrupt"})
            print("\n🛑 使用者手動中斷執行 (KeyboardInterrupt)")
            try:
                import subprocess

                subprocess.run(
                    [
                        "osascript",
                        "-e",
                        'display notification "Execution Interrupted" with title "Open-Claw"',
                    ],
                    check=False,
                )
            except Exception:
                pass
            sys.exit(130)
        except Exception as exc:
            self._write_session_state(
                SessionState.FAILED,
                context={"error": str(exc)},
            )
            print(f"💥 未預期錯誤: {exc}")

        if completed_normally and not any_stopped:
            self._write_session_state(SessionState.COMPLETED)
            self._state_manager.clear_checkpoint()

        print("🏁 Pipeline 執行完畢。")
        try:
            import subprocess

            subprocess.run(
                [
                    "osascript",
                    "-e",
                    'display notification "Pipeline 執行完畢" with title "Open-Claw"',
                ],
                check=False,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_skill_parser(
        "V8.0 Audio Transcriber Pipeline 三階段處理",
        include_subject=True,
        include_force=True,
        include_resume=True,
        include_interactive=True,
        include_start_phase=True,
    )
    parser.add_argument("--glossary", action="store_true", help="執行詞庫自動生成 (Phase 0)")
    parser.add_argument("--glossary-merge", action="store_true", help="合併現有詞庫")
    parser.add_argument("--glossary-force", action="store_true", help="強制重新生成詞庫")
    args = parser.parse_args()

    VoiceMemoOrchestrator().run(args)


if __name__ == "__main__":
    main()
