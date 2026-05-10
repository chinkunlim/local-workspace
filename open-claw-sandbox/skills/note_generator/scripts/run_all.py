"""
run_all.py — NoteGenerator Skill Orchestrator (V2.0)
=====================================================
Full pipeline runner with DAG tracking, StateManager integration,
checkpoint resume, <think> tag stripping, Mermaid auto-repair,
and asset directory copying.

Symmetrical to audio_transcriber / doc_parser architecture.

Modes:
  1. Batch mode: --subject / --file — processes all .md files in
     data/proofreader/output/00_doc_proofread/<subject>/
  2. File mode:  --input-file <path> --output-file <path> — single-file
     execution used by RouterAgent / CLI direct invocation.
"""

import argparse
import datetime
import os
import re
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
# Post-processing helpers
# ---------------------------------------------------------------------------


def strip_think_tags(text: str) -> str:
    """Remove <think>...</think> reasoning blocks emitted by reasoning models."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def fix_mermaid_syntax(text: str) -> str:
    """Normalize common Mermaid mindmap syntax errors produced by LLMs.

    Repairs:
    - ```mermaid\\n  mindmap true ... → ```mermaid\\nmindmap
    - Stray inline options after the mindmap keyword
    """

    def _clean_block(m: re.Match) -> str:
        block = m.group(1)
        # Normalise the mindmap declaration line
        block = re.sub(
            r"^\s*mindmap\s+(?:true\s+)?(?:padding\s+\S+\s+)?(?:width=\S+\s+)?(?:height=\S+)?",
            "mindmap",
            block,
            flags=re.MULTILINE,
        )
        return f"```mermaid{block}```"

    return re.sub(r"```mermaid(.*?)```", _clean_block, text, flags=re.DOTALL)


def _copy_assets(input_file: str, output_file: str) -> None:
    """Copy the assets/ directory next to input_file to the output directory."""
    input_dir = os.path.dirname(os.path.abspath(input_file))
    output_dir = os.path.dirname(os.path.abspath(output_file))
    src_assets = os.path.join(input_dir, "assets")
    dst_assets = os.path.join(output_dir, "assets")
    if os.path.isdir(src_assets) and src_assets != dst_assets:
        shutil.copytree(src_assets, dst_assets, dirs_exist_ok=True)


# ---------------------------------------------------------------------------
# Inner Phase: Synthesis (the core NoteGenerator logic)
# ---------------------------------------------------------------------------


class PhaseNoteGenerator(PipelineBase):
    """Phase N1 — Synthesize proofreader output into a structured study note."""

    def __init__(self, profile: str | None = None) -> None:
        super().__init__(
            phase_key="synthesize",
            phase_name="知識合成",
            skill_name="note_generator",
        )
        self.profile_override = profile

    # -- Mermaid validator -- #
    def _validate_mermaid(self, text: str) -> list[str]:
        errors = []
        blocks = re.findall(r"```mermaid(.*?)```", text, re.DOTALL)
        for idx, block in enumerate(blocks, 1):
            if "mindmap" not in block:
                errors.append(f"區塊 {idx}: 缺少 'mindmap' 宣告，心智圖語法無效。")
        return errors

    # -- Agentic Mermaid retry loop -- #
    def _agentic_mermaid_retry(
        self,
        node_text: str,
        base_prompt: str,
        model: str,
        options: dict,
        max_retries: int,
    ) -> tuple[str, str | None]:
        for attempt in range(1, max_retries + 1):
            errors = self._validate_mermaid(node_text)
            if not errors:
                return node_text, None
            error_str = "\n".join(errors)
            self.warning(f"⚠️ [Agentic Retry {attempt}/{max_retries}] Mermaid 語法錯誤: {error_str}")
            retry_prompt = (
                f"{base_prompt}\n\n"
                f"【上次生成的內容有語法錯誤。請修正以下 Mermaid 錯誤並重新輸出整份筆記】：\n{error_str}\n\n"
                f"【你的上一次輸出】：\n{node_text}"
            )
            pbar, stop_tick, t = self.create_spinner(f"Agentic 自我修正 ({attempt})")
            try:
                node_text = self.llm.generate(model=model, prompt=retry_prompt, options=options)
                node_text = strip_think_tags(node_text)
            except Exception as e:
                self.error(f"❌ Retry LLM 失敗: {e}")
                break
            finally:
                self.finish_spinner(pbar, stop_tick, t)

        errors = self._validate_mermaid(node_text)
        if errors:
            self.error(f"❌ 多次修正後仍然失敗格式: {errors}")
            return node_text, "Mermaid語法失效"
        return node_text, "自癒修正成功"

    # -- Map-Reduce for large inputs -- #
    def _synthesize_chunked(
        self,
        content: str,
        map_tpl: str,
        reduce_tpl: str,
        model: str,
        options: dict,
        label: str,
        map_size: int,
    ) -> tuple[str, int, int]:
        import asyncio

        chunks = smart_split(content, map_size)
        tc = len(chunks)
        self.info(f"   📦 大型輸入（{len(content):,} 字元），啟動 Map-Reduce ({tc} 個分塊)")

        map_prompts = [
            (
                map_tpl.replace("{INPUT_CONTENT}", chunk)
                if "{INPUT_CONTENT}" in map_tpl
                else f"{map_tpl}\n\n<transcript>\n{chunk}\n</transcript>"
            )
            for chunk in chunks
        ]

        self.info(f"   ⏳ 並發執行 {tc} 個 Map 任務 (max_concurrency=3)...")
        pbar, stop_tick, t = self.create_spinner(f"Map x{tc} ({label})")
        try:
            raw_map_results = asyncio.run(
                self.llm.async_batch_generate(
                    model=model,
                    prompts=map_prompts,
                    options=options,
                    max_concurrency=3,
                    logger=self,
                )
            )
        finally:
            self.finish_spinner(pbar, stop_tick, t)

        map_results = []
        map_success = 0
        for ci, extracted in enumerate(raw_map_results, 1):
            if extracted:
                cleaned = strip_think_tags(extracted)
                map_results.append(f"<!-- 分塊 {ci}/{tc} -->\n{cleaned.strip()}")
                map_success += 1
            else:
                self.warning(f"   ⚠️  Map [{ci}/{tc}] 失敗，跳過。")

        if not map_results:
            raise ValueError("Map 階段全部失敗。")

        cmb = "\n\n---\n\n".join(map_results)
        note = "以下是按段落提取的關鍵材料。請整合成一份結構化筆記。\n\n"
        fin_prompt = (
            reduce_tpl.replace("{INPUT_CONTENT}", note + cmb)
            if "{INPUT_CONTENT}" in reduce_tpl
            else f"{reduce_tpl}\n\n<materials>\n{note}{cmb}\n</materials>"
        )

        self.info(f"   🔗 Reduce：整合 {len(map_results)} 份摘要...")
        pbar, stop_tick, t = self.create_spinner(f"Reduce ({label})")
        try:
            final_note = self.llm.generate(model=model, prompt=fin_prompt, options=options)
            final_note = strip_think_tags(final_note)
        finally:
            self.finish_spinner(pbar, stop_tick, t)

        return final_note, map_success, tc

    # -- Main synthesis entry -- #
    def run_single(
        self,
        markdown_text: str,
        subject: str = "Default",
        label: str = "document",
        figure_list: str = "",
        glossary_injection: str = "",
    ) -> str:
        self.info(
            f"✨ [NoteGenerator] 啟動知識合成: [{subject}] {label} ({len(markdown_text):,} 字元)"
        )

        config = self.get_config("synthesize", subject_name=subject)

        if self.profile_override:
            profile_data = (
                self.config_manager.get_section("synthesize", {})
                .get("profiles", {})
                .get(self.profile_override)
            )
            if profile_data:
                config.update(profile_data)

        model = config.get("model")
        options = config.get("options", {})
        chunk_thresh = int(config.get("chunk_threshold", 6000))
        map_size = int(config.get("map_chunk_size", 4000))
        mermaid_retry_max = int(config.get("mermaid_retry_max", 2))
        min_retention_ratio = float(config.get("content_loss_threshold", 0.01))

        if not model:
            raise RuntimeError("note_generator: synthesize config missing model")

        reduce_tpl = self.get_prompt("Note Synthesis Instruction")
        map_tpl = self.get_prompt("Chunk Summary Extraction Instruction")

        if not reduce_tpl:
            self.error("❌ 找不到 Note Synthesis Instruction prompt")
            return ""
        if not map_tpl:
            self.warning("⚠️ 找不到 Map prompt，使用 Reduce 替代")
            map_tpl = reduce_tpl

        reduce_tpl = reduce_tpl.replace("{GLOSSARY}", glossary_injection).replace(
            "{FIGURES}", figure_list
        )
        map_tpl = map_tpl.replace("{GLOSSARY}", glossary_injection).replace(
            "{FIGURES}", figure_list
        )

        try:
            note_tag = None
            if len(markdown_text) > chunk_thresh:
                res, sc, tc = self._synthesize_chunked(
                    markdown_text, map_tpl, reduce_tpl, model, options, label, map_size
                )
                yaml_mr = "true"
                yaml_chk = f"{sc}/{tc}"
                if sc < tc:
                    note_tag = f"Map {sc}/{tc} 成功 (缺損)"
                    self.warning(f"⚠️ {note_tag}")
            else:
                pmpt = (
                    reduce_tpl.replace("{INPUT_CONTENT}", markdown_text)
                    if "{INPUT_CONTENT}" in reduce_tpl
                    else f"{reduce_tpl}\n\n<transcript>\n{markdown_text}\n</transcript>"
                )
                pbar, stop_tick, t = self.create_spinner(f"合成 ({label})")
                try:
                    res = self.llm.generate(model=model, prompt=pmpt, options=options)
                    res = strip_think_tags(res)
                finally:
                    self.finish_spinner(pbar, stop_tick, t)
                yaml_mr = "false"
                yaml_chk = "N/A"

            # Post-processing
            res = fix_mermaid_syntax(res)

            # Agentic Mermaid retry
            res, mm_tag = self._agentic_mermaid_retry(
                res, reduce_tpl, model, options, mermaid_retry_max
            )
            if mm_tag and not note_tag:
                note_tag = mm_tag

            # Content-Loss Guard
            retention_ratio = len(res) / max(1, len(markdown_text))
            self.info(
                f"📊 [NoteGenerator] 壓縮率檢核: 最終 {len(res):,} 字 / 原始 {len(markdown_text):,} 字 "
                f"(保留率 {retention_ratio:.1%})"
            )
            if retention_ratio < min_retention_ratio:
                raise ValueError(
                    f"[Content-loss Guard] 保留率 {retention_ratio:.1%} 低於下限 {min_retention_ratio:.1%}！"
                )

            # YAML Frontmatter
            now_str = datetime.datetime.now().isoformat("T", "seconds")
            yaml_header = (
                f"---\n"
                f"subject: {subject}\n"
                f"label: {label}\n"
                f"generated_at: {now_str}\n"
                f"model: {model}\n"
                f"map_reduce: {yaml_mr}\n"
                f"map_chunks: {yaml_chk}\n"
                f"source_chars: {len(markdown_text)}\n"
                f"output_chars: {len(res)}\n"
                f"pipeline_version: v2.0.0-orchestrator\n"
                f"---\n\n"
            )
            final_doc = yaml_header + res

        except Exception as e:
            self.error(f"❌ 合成失敗: {e}")
            raise e
        finally:
            self.llm.unload_model(model, logger=self)

        # DAG state tracking (best-effort)
        try:
            self.state_manager.update_task(
                subject=subject,
                filename=f"{label}.md",
                phase_key="synthesize",
                status="✅",
                char_count=len(final_doc),
            )
        except Exception:
            pass

        return final_doc


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class NoteGeneratorOrchestrator(PipelineBase):
    """Full note_generator pipeline orchestrator with DAG tracking."""

    def __init__(self) -> None:
        super().__init__(
            phase_key="orchestrator",
            phase_name="Note Generator 管線協調器",
            skill_name="note_generator",
        )
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        proofread_dir = os.path.join(
            workspace_root, "data", "proofreader", "output", "00_doc_proofread"
        )
        self._state_manager = StateManager(
            self.base_dir, skill_name="note_generator", raw_dir=proofread_dir
        )

    # ------------------------------------------------------------------ #
    #  Startup                                                             #
    # ------------------------------------------------------------------ #

    def startup_check(self) -> bool:
        import requests

        print("=" * 50)
        print("✈️  進行啟動前置檢查 (Preflight Check)...")
        fail = False

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
        import pathlib

        input_text = pathlib.Path(args.input_file).read_text(encoding="utf-8")
        subject = args.subject or "Default"
        label = getattr(args, "label", None) or os.path.splitext(os.path.basename(args.input_file))[
            0
        ].replace("_proofread", "")

        phase = PhaseNoteGenerator(profile=getattr(args, "profile", None))
        result = phase.run_single(input_text, subject=subject, label=label)

        output_path = args.output_file
        if not output_path:
            stem = os.path.splitext(args.input_file)[0].replace("_proofread", "")
            output_path = stem + "_notes.md"

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        _copy_assets(args.input_file, output_path)
        AtomicWriter.write_text(output_path, result)
        print(f"✅ Note written to: {output_path}")

    # ------------------------------------------------------------------ #
    #  Batch Mode                                                          #
    # ------------------------------------------------------------------ #

    def run(self, args: argparse.Namespace) -> None:
        if args.input_file:
            self.run_file_mode(args)
            return

        if not self.startup_check():
            sys.exit(1)

        self._state_manager.sync_physical_files()
        self._state_manager.print_dashboard()

        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        input_root = os.path.join(
            workspace_root, "data", "proofreader", "output", "00_doc_proofread"
        )
        output_root = os.path.join(workspace_root, "data", "note_generator", "output")

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
                    label = md_name.replace("_proofread.md", "")
                    out_name = label + "_notes.md"
                    output_path = os.path.join(output_root, subj, out_name)

                    if os.path.exists(output_path) and not args.force:
                        self.info(f"   ⏭️  已存在，跳過: [{subj}] {md_name}")
                        continue

                    print(f"\n{'=' * 50}")
                    print(f"🚀 合成: [{subj}] {md_name}")
                    print(f"{'=' * 50}")

                    with open(input_path, encoding="utf-8") as f:
                        text = f.read()
                    phase = PhaseNoteGenerator()
                    result = phase.run_single(text, subject=subj, label=label)

                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    _copy_assets(input_path, output_path)
                    AtomicWriter.write_text(output_path, result)

                    try:
                        self._state_manager.update_task(
                            subject=subj,
                            filename=md_name,
                            phase_key="synthesize",
                            status="✅",
                            char_count=len(result),
                        )
                    except Exception:
                        pass
                        
                    # --- Per-file EventBus Handoff ---
                    EventBus.publish(
                        DomainEvent(
                            name="PipelineCompleted",
                            source_skill="note_generator",
                            payload={"filepath": output_path, "subject": subj, "chain": []},
                        )
                    )

                    self._state_manager = StateManager(
                        self.base_dir,
                        skill_name="note_generator",
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

                    if args.interactive:
                        try:
                            print("✋ 已完成此文件。請按 [Enter] 繼續...")
                            input()
                        except (EOFError, KeyboardInterrupt):
                            pass

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
        "V2.0 Note Generator Pipeline — 知識合成筆記",
        include_subject=True,
        include_force=True,
        include_resume=True,
        include_interactive=True,
        include_start_phase=False,
    )
    parser.add_argument(
        "--input-file", dest="input_file", help="單一輸入 .md 檔案路徑 (RouterAgent / CLI)"
    )
    parser.add_argument(
        "--output-file", dest="output_file", help="單一輸出 .md 檔案路徑 (RouterAgent / CLI)"
    )
    parser.add_argument("--label", default=None, help="文件標籤 (YAML 標頭，預設從檔名推導)")
    parser.add_argument(
        "--profile",
        default=None,
        help="Config profile override (qwen3_reasoning/phi4_reasoning/default)",
    )
    args = parser.parse_args()

    NoteGeneratorOrchestrator().run(args)


if __name__ == "__main__":
    main()
