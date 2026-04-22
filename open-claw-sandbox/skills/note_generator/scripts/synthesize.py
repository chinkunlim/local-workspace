"""
NoteGenerator — Standalone skill for Markdown synthesis
========================================================
Synthesizes long Markdown texts into structured study notes
with YAML headers and Mermaid mindmaps.

Includes Map-Reduce chunking for large texts and Agentic
Mermaid retry loops for self-healing syntax generation.
"""

import datetime
import os
import re
import sys

# Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import PipelineBase
from core.text_utils import smart_split


class NoteGenerator(PipelineBase):
    def __init__(self, profile: str = None):
        super().__init__(
            phase_key="synthesize",
            phase_name="Note Generator",
            skill_name="note-generator",
        )
        self.profile_override = profile

    def _validate_mermaid(self, text: str) -> list:
        errors = []
        blocks = re.findall(r"```mermaid(.*?)```", text, re.DOTALL)
        for idx, block in enumerate(blocks, 1):
            if "mindmap" not in block:
                errors.append(f"區塊 {idx}: 缺少 'mindmap' 宣告，心智圖語法無效。")
        return errors

    def _agentic_mermaid_retry(
        self, node_text: str, base_prompt: str, model: str, options: dict, max_retries: int
    ) -> str:
        """Agentic loop to fix Mermaid syntax errors."""
        for attempt in range(1, max_retries + 1):
            errors = self._validate_mermaid(node_text)
            if not errors:
                return node_text, None  # Success

            error_str = "\n".join(errors)
            self.warning(
                f"⚠️ [Agentic Retry {attempt}/{max_retries}] 偵測到 Mermaid 語法錯誤: {error_str}"
            )

            retry_prompt = (
                f"{base_prompt}\n\n"
                f"【上次生成的內容有語法錯誤。請修正以下 Mermaid 錯誤並重新輸出整份筆記】：\n{error_str}\n\n"
                f"【你的上一次輸出】：\n{node_text}"
            )

            pbar, stop_tick, t = self.create_spinner(f"Agentic 自我修正 ({attempt})")
            try:
                node_text = self.llm.generate(model=model, prompt=retry_prompt, options=options)
            except Exception as e:
                self.error(f"❌ Retry LLM 失敗: {e}")
                break
            finally:
                self.finish_spinner(pbar, stop_tick, t)

        # Check again after retries
        errors = self._validate_mermaid(node_text)
        if errors:
            self.error(f"❌ 多次修正後仍然失敗格式: {errors}")
            return node_text, "Mermaid語法失效"
        return node_text, "自癒修正成功"

    def _synthesize_chunked(
        self,
        content: str,
        map_tpl: str,
        reduce_tpl: str,
        model: str,
        options: dict,
        label: str,
        map_size: int,
    ):
        chunks = smart_split(content, map_size)
        tc = len(chunks)
        self.info(f"   📦 大型輸入（{len(content):,} 字元），啟動 Map-Reduce ({tc} 個分塊)")

        map_results = []
        map_success = 0
        for ci, chunk in enumerate(chunks, 1):
            if self.stop_requested:
                break
            self.info(f"   🗂  Map [{ci}/{tc}]：提取關鍵材料...")
            prompt = (
                map_tpl.replace("{INPUT_CONTENT}", chunk)
                if "{INPUT_CONTENT}" in map_tpl
                else f"{map_tpl}\n\n<transcript>\n{chunk}\n</transcript>"
            )

            pbar, stop_tick, t = self.create_spinner(f"Map {ci}/{tc} ({label})")
            try:
                extracted = self.llm.generate(model=model, prompt=prompt, options=options)
                map_results.append(f"<!-- 分塊 {ci}/{tc} -->\n{extracted.strip()}")
                map_success += 1
            except Exception as e:
                self.warning(f"   ⚠️  Map [{ci}/{tc}] 失敗: {e}，跳過。")
            finally:
                self.finish_spinner(pbar, stop_tick, t)

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
        finally:
            self.finish_spinner(pbar, stop_tick, t)

        return final_note, map_success, tc

    def run(
        self,
        markdown_text: str,
        subject: str = "Default",
        label: str = "document",
        figure_list: str = "",
        glossary_injection: str = "",
    ) -> str:
        """
        Generate a structured study note from the input Markdown text.

        Args:
            markdown_text: Raw Markdown text to synthesize.
            subject: Subject label for config and YAML header.
            label: Document label (e.g. lecture base name) for YAML header.
            figure_list: Optional string of figures to inject into prompt.
            glossary_injection: Optional glossary prompt block.

        Returns:
            The final synthesized Markdown note with YAML frontmatter.
        """
        self.info(
            f"✨ [NoteGenerator] 啟動知識合成: [{subject}] {label} ({len(markdown_text):,} 字元)"
        )

        config = self.get_config("synthesize", subject_name=subject)

        # Override active profile if specified
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
            raise RuntimeError("note-generator synthesize config missing model")

        reduce_tpl = self.get_prompt("Phase 5: 筆記合成指令")
        map_tpl = self.get_prompt("Phase 5 Part A: 分塊摘要提取指令")

        if not reduce_tpl:
            self.error("❌ 找不到 Phase 5: 筆記合成指令 prompt")
            return ""
        if not map_tpl:
            self.warning("⚠️ 找不到 Map prompt，使用 Reduce 替代")
            map_tpl = reduce_tpl

        # Inject dynamic context (Glossary & Figures)
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
                finally:
                    self.finish_spinner(pbar, stop_tick, t)
                yaml_mr = "false"
                yaml_chk = "N/A"

            # Agentic Mermaid Retry
            res, mm_tag = self._agentic_mermaid_retry(
                res, reduce_tpl, model, options, mermaid_retry_max
            )
            if mm_tag and not note_tag:
                note_tag = mm_tag

            # Content-Loss Guard
            retention_ratio = len(res) / max(1, len(markdown_text))
            self.info(
                f"📊 [NoteGenerator] 壓縮率檢核: 最終 {len(res):,} 字 / 原始 {len(markdown_text):,} 字 (保留率 {retention_ratio:.1%})"
            )

            if retention_ratio < min_retention_ratio:
                raise ValueError(
                    f"[Content-loss Guard] 筆記保留率 {retention_ratio:.1%} 低於下限 {min_retention_ratio:.1%}！"
                )

            # YAML Frontmatter
            now_str = datetime.datetime.now().isoformat("T", "seconds")
            yaml_header = f"---\nsubject: {subject}\nlabel: {label}\ngenerated_at: {now_str}\nmodel: {model}\nmap_reduce: {yaml_mr}\nmap_chunks: {yaml_chk}\nsource_chars: {len(markdown_text)}\noutput_chars: {len(res)}\npipeline_version: v1.0.0-standalone\n---\n\n"

            final_doc = yaml_header + res

        except Exception as e:
            self.error(f"❌ 合成失敗: {e}")
            raise e
        finally:
            self.llm.unload_model(model, logger=self)

        return final_doc


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Note Generator Skill")
    parser.add_argument("--subject", default="Default", help="Subject label")
    parser.add_argument("--label", default="document", help="Document label")
    parser.add_argument("--profile", help="Config profile override")
    parser.add_argument("--input-file", dest="input_file", help="Input .md file path (file mode)")
    parser.add_argument(
        "--output-file", dest="output_file", help="Output .md file path (file mode)"
    )
    args = parser.parse_args()

    generator = NoteGenerator(profile=args.profile)

    # File mode (WebUI Re-run)
    if args.input_file:
        import pathlib

        input_text = pathlib.Path(args.input_file).read_text(encoding="utf-8")
        result = generator.run(input_text, subject=args.subject, label=args.label)
        if args.output_file:
            from core.atomic_writer import AtomicWriter

            AtomicWriter.write_text(args.output_file, result)
            print(f"✅ Note written to: {args.output_file}")
        else:
            print(result)

    # Stdin mode (legacy / CLI testing)
    elif not sys.stdin.isatty():
        input_text = sys.stdin.read()
        if input_text:
            result = generator.run(input_text, subject=args.subject, label=args.label)
            print(result)
    else:
        print(
            "Usage: cat doc.md | python synthesize.py  OR  python synthesize.py --input-file doc.md --output-file out.md"
        )
