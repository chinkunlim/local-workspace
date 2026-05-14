"""
run_all.py — SmartHighlighter Skill Orchestrator (V3.0)
========================================================
Full pipeline runner with DAG tracking, StateManager integration,
checkpoint resume, and asset directory copying.

Symmetrical to audio_transcriber / doc_parser architecture.

Modes:
  1. Batch mode: --subject / --file — processes all .md files in
     data/proofreader/output/04_final_verified/<subject>/
  2. File mode:  --input-file <path> --output-file <path> — single-file
     execution used by RouterAgent / CLI direct invocation.
"""

import argparse
import os
import shutil
import sys
from typing import Optional

# Group 2 — Internal Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

# Group 3 — Core imports
from core import (
    PipelineBase,
    SessionState,
    StateManager,
    build_skill_parser,
)
from core.orchestration.event_bus import DomainEvent, EventBus
from core.utils.atomic_writer import AtomicWriter
from core.utils.text_utils import smart_split

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _copy_assets(input_file: str, output_file: str) -> None:
    """Copy the assets/ directory next to input_file to the output directory."""
    input_dir = os.path.dirname(os.path.abspath(input_file))
    output_dir = os.path.dirname(os.path.abspath(output_file))
    src_assets = os.path.join(input_dir, "assets")
    dst_assets = os.path.join(output_dir, "assets")
    if os.path.isdir(src_assets) and src_assets != dst_assets:
        shutil.copytree(src_assets, dst_assets, dirs_exist_ok=True)


# ---------------------------------------------------------------------------
# Inner Phase: Highlight
# ---------------------------------------------------------------------------


class PhaseHighlight(PipelineBase):
    """Phase H1 — Smart annotation using Markdown markup."""

    DEFAULT_VERBATIM_THRESHOLD: float = 0.85

    def __init__(self, profile: str | None = None) -> None:
        super().__init__(
            phase_key="highlight",
            phase_name="重點標記",
            skill_name="smart_highlighter",
        )
        self.profile_override = profile

        # Route inbox to proofreader output, and processed to our output
        workspace_root = os.path.abspath(os.path.join(self.base_dir, "..", "..", ".."))
        self.dirs["inbox"] = os.path.join(
            workspace_root, "data", "proofreader", "output", "04_final_verified"
        )
        self.dirs["processed"] = os.path.join(workspace_root, "data", "smart_highlighter", "output")
        self.dirs["error"] = os.path.join(workspace_root, "data", "smart_highlighter", "error")
        # Ensure raw maps to the proofreader inbox for File matching
        self.dirs["raw"] = self.dirs["inbox"]

    def run(
        self,
        force: bool = False,
        subject: str = None,
        file_filter: str = None,
        single_mode: bool = False,
        resume_from: dict = None,
    ) -> None:
        self.process_tasks(
            self._process_file,
            force=force,
            subject_filter=subject,
            file_filter=file_filter,
            single_mode=single_mode,
            resume_from=resume_from,
        )

    def _process_file(self, idx: int, task: dict, total: int) -> Optional[bool]:
        subject = task["subject"]
        filename = task["filename"]

        # Exclude non-markdown
        if not filename.endswith(".md"):
            return False

        input_path = os.path.join(self.dirs.get("inbox", ""), subject, filename)

        out_name = filename.replace("_proofread.md", "_highlighted.md")
        # if it doesn't have _proofread suffix, fallback
        if out_name == filename:
            stem = os.path.splitext(filename)[0]
            out_name = f"{stem}_highlighted.md"

        output_path = os.path.join(self.dirs["processed"], subject, out_name)

        self.info(f"🚀 [Phase H1] 標記: [{subject}] {filename}")

        if not os.path.exists(input_path):
            self.error(f"❌ 找不到檔案: {input_path}")
            self.state_manager.update_task(subject, filename, self.phase_key, "❌")
            return False

        with open(input_path, encoding="utf-8") as f:
            text = f.read()

        result = self.run_single(text, subject=subject)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        _copy_assets(input_path, output_path)
        AtomicWriter.write_text(output_path, result)

        self.state_manager.update_task(
            subject=subject,
            filename=filename,
            phase_key=self.phase_key,
            status="✅",
            char_count=len(result),
        )

        EventBus.publish(
            DomainEvent(
                name="PipelineCompleted",
                source_skill="smart_highlighter",
                payload={"filepath": output_path, "subject": subject, "chain": []},
            )
        )
        return True

    def run_single(
        self,
        markdown_text: str,
        subject: str = "Default",
    ) -> str:
        """Annotate a single markdown string. Returns the annotated text."""
        config = self.get_config("highlight", subject_name=subject)

        if self.profile_override:
            profile_data = (
                self.config_manager.get_section("highlight", {})
                .get("profiles", {})
                .get(self.profile_override)
            )
            if profile_data:
                config.update(profile_data)

        model_name = config.get("model")
        options = config.get("options", {})
        chunk_size = int(config.get("chunk_size", 3000))
        min_chunk_chars = int(config.get("min_chunk_chars", 30))
        verbatim_threshold = float(
            config.get("verbatim_threshold", self.DEFAULT_VERBATIM_THRESHOLD)
        )

        if not model_name:
            raise RuntimeError("smart_highlighter: config missing model")

        prompt_tpl = self.get_prompt("Highlight: Key Annotation Instruction")
        if not prompt_tpl:
            self.error(
                "❌ 找不到 prompt，請確認 prompt.md 有「Highlight: Key Annotation Instruction」段落"
            )
            return markdown_text

        chunks = smart_split(markdown_text, chunk_size)
        self.info(f"📦 [SmartHighlighter] 共 {len(chunks)} 個片段待標記 (模型: {model_name})")

        highlighted_parts = []
        pbar, stop_tick, t = self.create_spinner("標記")

        try:
            for idx, chunk in enumerate(chunks, 1):
                if self.stop_requested:
                    self.warning("⚠️  收到中止信號，停止標記")
                    break

                if len(chunk.strip()) < min_chunk_chars:
                    highlighted_parts.append(chunk)
                    continue

                prompt = f"{prompt_tpl}\n\n[原文片段]:\n{chunk}"

                try:
                    result = self.llm.generate(
                        model=model_name,
                        prompt=prompt,
                        options=options,
                        logger=self,
                    )
                    if len(result.strip()) < len(chunk) * verbatim_threshold:
                        self.warning(
                            f"   ⚠️  片段 {idx} [防竄改]: LLM 輸出過短 "
                            f"({len(result.strip())} < {len(chunk) * verbatim_threshold:.0f})，還原原文"
                        )
                        highlighted_parts.append(chunk)
                    else:
                        highlighted_parts.append(result.strip())
                except Exception as e:
                    self.error(f"   ❌ 片段 {idx} 標記失敗: {e}，還原原文")
                    highlighted_parts.append(chunk)
        finally:
            self.finish_spinner(pbar, stop_tick, t)
            self.llm.unload_model(model_name, logger=self)

        return "\n\n".join(highlighted_parts)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class SmartHighlighterOrchestrator(PipelineBase):
    """Full smart_highlighter pipeline orchestrator with DAG tracking."""

    def __init__(self) -> None:
        super().__init__(
            phase_key="orchestrator",
            phase_name="Smart Highlighter 管線協調器",
            skill_name="smart_highlighter",
        )
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        inbox_dir = os.path.join(
            workspace_root, "data", "proofreader", "output", "04_final_verified"
        )
        self._state_manager = StateManager(
            self.base_dir, skill_name="smart_highlighter", raw_dir=inbox_dir
        )

    # ------------------------------------------------------------------ #
    #  Startup                                                             #
    # ------------------------------------------------------------------ #

    def startup_check(self) -> bool:
        import requests

        print("=" * 50)
        print("✈️  進行啟動前置檢查 (Preflight Check)...")
        fail = False

        # 1. Check Ollama
        try:
            ollama_cfg = self.config_manager.get_section("runtime", {}).get("ollama", {})
            api_url = ollama_cfg.get("api_url", "http://127.0.0.1:11434/api/generate")
            tags_url = api_url.replace("/api/generate", "/api/tags")
            requests.get(tags_url, timeout=3).raise_for_status()
        except Exception:
            print("❌ 錯誤：無法連線至 Ollama (`ollama serve`)。")
            fail = True

        if fail:
            return False
        print("✅ 前置檢查通過。")
        return True

    # ------------------------------------------------------------------ #
    #  File Mode (single --input-file execution)                          #
    # ------------------------------------------------------------------ #

    def run_file_mode(self, args: argparse.Namespace) -> None:
        """Process a single file given via --input-file / --output-file."""
        import pathlib

        if not args.input_file:
            print("❌ 需要指定 --input-file")
            sys.exit(1)

        input_text = pathlib.Path(args.input_file).read_text(encoding="utf-8")
        subject = getattr(args, "subject", None) or "Default"

        phase = PhaseHighlight(profile=getattr(args, "profile", None))
        result = phase.run_single(input_text, subject=subject)

        output_path = args.output_file
        if not output_path:
            stem = os.path.splitext(args.input_file)[0]
            output_path = stem + "_highlighted.md"

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        _copy_assets(args.input_file, output_path)
        AtomicWriter.write_text(output_path, result)
        print(f"✅ Highlighted output written to: {output_path}")

    # ------------------------------------------------------------------ #
    #  Batch Mode                                                          #
    # ------------------------------------------------------------------ #

    def run(self, args: argparse.Namespace) -> None:
        """Execute the full smart_highlighter pipeline."""
        if getattr(args, "input_file", None):
            self.run_file_mode(args)
            return

        if not self.startup_check():
            sys.exit(1)

        self._state_manager.sync_physical_files()

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

        completed_normally = False
        any_stopped = False
        try:
            print(f"\n{'=' * 50}")
            print("🚀 開始執行重點標記 (Phase H1)...")
            print(f"{'=' * 50}")

            p_obj = PhaseHighlight(profile=getattr(args, "profile", None))

            phase_resume = None
            if resume_from and resume_from.get("phase_key", "") == p_obj.phase_key:
                phase_resume = resume_from

            p_obj.run(
                force=args.force,
                subject=args.subject,
                file_filter=getattr(args, "file", None),
                single_mode=False,
                resume_from=phase_resume,
            )

            if p_obj.stop_requested:
                any_stopped = True
                if p_obj.pause_requested:
                    self._write_session_state(SessionState.PAUSED)
                    print("💾 Pipeline 已暫停並儲存進度，下次執行自動從斷點繼續。")
                else:
                    self._write_session_state(SessionState.STOPPED)
                    self._state_manager.clear_checkpoint()
                    print("🛑 Pipeline 已停止（不儲存進度）。")

            if not any_stopped:
                completed_normally = True

        except SystemExit:
            pass
        except KeyboardInterrupt:
            print("\n\n⏸️  已收到 Ctrl+C...")
            saved = False
            try:
                choice = (
                    input("  請選擇: [S] 儲存進度並離開  [Q] 直接離開 (S/Q) [Enter = S]: ")
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt):
                choice = "q"

            if choice != "q":
                cp_path = os.path.join(self.base_dir, "state", "checkpoint.json")
                if os.path.exists(cp_path):
                    saved = True
                self._write_session_state(SessionState.PAUSED, context={"interrupted": True})
                print("💾 進度已儲存。下次執行會自動從斷點繼續。")
            else:
                self._write_session_state(
                    SessionState.STOPPED, context={"error": "KeyboardInterrupt"}
                )
                self._state_manager.clear_checkpoint()
                print("🛑 已離開，未儲存進度。")
            PipelineBase.notify_os("執行已中斷")
            sys.exit(130)
        except Exception as exc:
            self._write_session_state(SessionState.FAILED, context={"error": str(exc)})
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
        "V3.0 Smart Highlighter Pipeline — Markdown 重點標記",
        include_subject=True,
        include_force=True,
        include_resume=True,
        include_interactive=False,
        include_start_phase=False,
    )
    parser.add_argument(
        "--input-file", dest="input_file", help="單一輸入 .md 檔案路徑 (RouterAgent / CLI)"
    )
    parser.add_argument(
        "--output-file", dest="output_file", help="單一輸出 .md 檔案路徑 (RouterAgent / CLI)"
    )
    parser.add_argument("--profile", help="Config profile override (default/strict/fast)")
    args = parser.parse_args()

    SmartHighlighterOrchestrator().run(args)


if __name__ == "__main__":
    main()
