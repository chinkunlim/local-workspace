"""
run_all.py — SmartHighlighter Skill Orchestrator (V2.0)
========================================================
Full pipeline runner with DAG tracking, StateManager integration,
checkpoint resume, and asset directory copying.

Symmetrical to audio_transcriber / doc_parser / note_generator architecture.

Modes:
  1. Batch mode: --subject / --file — processes all .md files in
     data/proofreader/output/00_doc_proofread/<subject>/
  2. File mode:  --input-file <path> --output-file <path> — single-file
     execution used by RouterAgent / CLI direct invocation.
"""

import argparse
import os
import shutil
import sys

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


def _copy_assets(input_file: str, output_file: str) -> None:
    """Copy the assets/ directory next to input_file to the output directory."""
    input_dir = os.path.dirname(os.path.abspath(input_file))
    output_dir = os.path.dirname(os.path.abspath(output_file))
    src_assets = os.path.join(input_dir, "assets")
    dst_assets = os.path.join(output_dir, "assets")
    if os.path.isdir(src_assets) and src_assets != dst_assets:
        shutil.copytree(src_assets, dst_assets, dirs_exist_ok=True)


class SmartHighlighterOrchestrator(PipelineBase):
    """Full smart_highlighter pipeline orchestrator with DAG tracking."""

    def __init__(self) -> None:
        super().__init__(
            phase_key="orchestrator",
            phase_name="Smart Highlighter 管線協調器",
            skill_name="smart_highlighter",
        )
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        proofread_dir = os.path.join(
            workspace_root, "data", "proofreader", "output", "00_doc_proofread"
        )
        self._state_manager = StateManager(
            self.base_dir, skill_name="smart_highlighter", raw_dir=proofread_dir
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
        subject = args.subject or "Default"

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
        if args.input_file:
            self.run_file_mode(args)
            return

        if not self.startup_check():
            sys.exit(1)

        self._state_manager.sync_physical_files()
        self._state_manager.print_dashboard()

        # Resolve input root — proofreader output
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        input_root = os.path.join(
            workspace_root, "data", "proofreader", "output", "00_doc_proofread"
        )
        output_root = os.path.join(workspace_root, "data", "smart_highlighter", "output")

        # Gather subjects
        subject_filter = args.subject
        subjects = (
            [subject_filter]
            if subject_filter
            else sorted(
                d for d in os.listdir(input_root) if os.path.isdir(os.path.join(input_root, d))
            )
        )

        completed_normally = False
        try:
            for subj in subjects:
                subj_dir = os.path.join(input_root, subj)
                if not os.path.isdir(subj_dir):
                    continue

                md_files = sorted(f for f in os.listdir(subj_dir) if f.endswith(".md"))

                for md_name in md_files:
                    if args.file and args.file != md_name:
                        continue

                    input_path = os.path.join(subj_dir, md_name)
                    out_name = md_name.replace("_proofread.md", "_highlighted.md")
                    output_path = os.path.join(output_root, subj, out_name)

                    if os.path.exists(output_path) and not args.force:
                        self.info(f"   ⏭️  已存在，跳過: [{subj}] {md_name}")
                        continue

                    print(f"\n{'=' * 50}")
                    print(f"🚀 標記: [{subj}] {md_name}")
                    print(f"{'=' * 50}")

                    with open(input_path, encoding="utf-8") as f:
                        text = f.read()
                    phase = PhaseHighlight()
                    result = phase.run_single(text, subject=subj)

                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    _copy_assets(input_path, output_path)
                    AtomicWriter.write_text(output_path, result)

                    try:
                        self._state_manager.update_task(
                            subject=subj,
                            filename=md_name,
                            phase_key="highlight",
                            status="✅",
                            char_count=len(result),
                        )
                    except Exception:
                        pass

                    # --- Per-file EventBus Handoff ---
                    EventBus.publish(
                        DomainEvent(
                            name="PipelineCompleted",
                            source_skill="smart_highlighter",
                            payload={"filepath": output_path, "subject": subj, "chain": []},
                        )
                    )

                    self._state_manager = StateManager(
                        self.base_dir,
                        skill_name="smart_highlighter",
                        raw_dir=os.path.abspath(
                            os.path.join(
                                os.path.dirname(__file__),
                                "..",
                                "..",
                                "..",
                                "data",
                                "proofreader",
                                "output",
                                "00_doc_proofread",
                            )
                        ),
                    )
                    self._state_manager.print_dashboard()

            completed_normally = True
        except KeyboardInterrupt:
            self._write_session_state(SessionState.STOPPED, context={"error": "KeyboardInterrupt"})
            print("\n🛑 使用者手動中斷執行 (KeyboardInterrupt)")
            sys.exit(130)
        except Exception as exc:
            self._write_session_state(SessionState.FAILED, context={"error": str(exc)})
            print(f"💥 未預期錯誤: {exc}")

        if completed_normally:
            self._write_session_state(SessionState.COMPLETED)

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
        "V2.0 Smart Highlighter Pipeline — Markdown 重點標記",
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
