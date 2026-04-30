"""
SmartHighlighter — Standalone skill for Markdown annotation
===========================================================
Applies Markdown annotations (bold, highlight, code) to input text.
Stateless design: receives text, returns text.

Anti-Tampering guard ensures the LLM does not delete content.
"""

import os
import sys

# Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import PipelineBase
from core.utils.text_utils import smart_split


class SmartHighlighter(PipelineBase):
    DEFAULT_VERBATIM_THRESHOLD: float = 0.85

    def __init__(self, profile: str = None):
        super().__init__(
            phase_key="highlight",
            phase_name="Smart Highlighter",
            skill_name="smart-highlighter",
        )
        self.profile_override = profile

    def run(self, markdown_text: str, subject: str = "Default") -> str:
        """
        Apply Markdown bold/highlight annotations to the input text.

        Args:
            markdown_text: The raw Markdown string to annotate.
            subject: The subject label (used for logging and config selection).

        Returns:
            The annotated Markdown string.
        """
        self.info(f"🖊️  [SmartHighlighter] 啟動重點標記: [{subject}] ({len(markdown_text):,} 字元)")

        config = self.get_config("highlight", subject_name=subject)

        # Override active profile if specified
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
            raise RuntimeError("smart-highlighter highlight config missing model")

        prompt_tpl = self.get_prompt("Phase 4: 重點標記指令")
        if not prompt_tpl:
            self.error("❌ 找不到 prompt 指令，請確認 prompt.md 有「Phase 4: 重點標記指令」段落")
            return markdown_text  # Fallback to original

        chunks = smart_split(markdown_text, chunk_size)
        self.info(
            f"\U0001f4e6 [SmartHighlighter] \u5171 {len(chunks)} \u500b\u7247\u6bb5\u5f85\u6a19\u8a18 (\u6a21\u578b: {model_name})"
        )

        highlighted_parts = []
        pbar, stop_tick, t = self.create_spinner("\u6a19\u8a18")

        try:  # M2: guarantee unload_model even if an exception escapes the chunk loop
            for idx, chunk in enumerate(chunks, 1):
                if self.stop_requested:
                    self.warning(
                        "\u26a0\ufe0f  [SmartHighlighter] \u6536\u5230\u4e2d\u6b62\u4fe1\u865f\uff0c\u505c\u6b62\u6a19\u8a18"
                    )
                    break

                if len(chunk.strip()) < min_chunk_chars:
                    highlighted_parts.append(chunk)
                    continue

                prompt = f"{prompt_tpl}\n\n[\u539f\u6587\u7247\u6bb5]:\n{chunk}"

                try:
                    result = self.llm.generate(
                        model=model_name,
                        prompt=prompt,
                        options=options,
                        logger=self,
                    )

                    # Anti-Tampering guard
                    if len(result.strip()) < len(chunk) * verbatim_threshold:
                        self.warning(
                            f"   \u26a0\ufe0f  \u7247\u6bb5 {idx} [\u9632\u7ac4\u6539\u89f8\u767c]: LLM \u8f38\u51fa\u904e\u77ed "
                            f"({len(result.strip())} < {len(chunk) * verbatim_threshold:.0f})\uff0c\u9084\u539f\u539f\u6587"
                        )
                        highlighted_parts.append(chunk)
                    else:
                        highlighted_parts.append(result.strip())
                except Exception as e:
                    self.error(
                        f"   \u274c \u7247\u6bb5 {idx} \u6a19\u8a18\u5931\u6557: {e}\uff0c\u9084\u539f\u539f\u6587"
                    )
                    highlighted_parts.append(chunk)
        finally:
            self.finish_spinner(pbar, stop_tick, t)
            self.llm.unload_model(model_name, logger=self)  # M2: always executes

        return "\n\n".join(highlighted_parts)


if __name__ == "__main__":
    try:
        import argparse

        parser = argparse.ArgumentParser(description="Smart Highlighter Skill")
        parser.add_argument("--subject", default="Default", help="Subject label")
        parser.add_argument("--profile", help="Config profile override")
        parser.add_argument(
            "--input-file", dest="input_file", help="Input .md file path (file mode)"
        )
        parser.add_argument(
            "--output-file", dest="output_file", help="Output .md file path (file mode)"
        )
        args = parser.parse_args()

        highlighter = SmartHighlighter(profile=args.profile)

        # File mode (WebUI Re-run)
        if args.input_file:
            import pathlib

            input_text = pathlib.Path(args.input_file).read_text(encoding="utf-8")
            result = highlighter.run(input_text, subject=args.subject)
            if args.output_file:
                from core.utils.atomic_writer import AtomicWriter

                AtomicWriter.write_text(args.output_file, result)
                print(f"✅ Highlighted output written to: {args.output_file}")
            else:
                print(result)

        # Stdin mode (legacy / CLI testing)
        elif not sys.stdin.isatty():
            input_text = sys.stdin.read()
            if input_text:
                result = highlighter.run(input_text, subject=args.subject)
                print(result)
        else:
            print(
                "Usage: cat doc.md | python highlight.py  OR  python highlight.py --input-file doc.md --output-file out.md"
            )
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
    except KeyboardInterrupt:
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
        import sys

        sys.exit(130)
