# -*- coding: utf-8 -*-
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
from core.bootstrap import ensure_core_path as _bootstrap
_bootstrap(__file__)

from core import PipelineBase
from core.text_utils import smart_split


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
            profile_data = self.config_manager.get_section("highlight", {}).get("profiles", {}).get(self.profile_override)
            if profile_data:
                config.update(profile_data)
                
        model_name = config.get("model")
        options = config.get("options", {})
        chunk_size = int(config.get("chunk_size", 3000))
        min_chunk_chars = int(config.get("min_chunk_chars", 30))
        verbatim_threshold = float(config.get("verbatim_threshold", self.DEFAULT_VERBATIM_THRESHOLD))
        
        if not model_name:
            raise RuntimeError("smart-highlighter highlight config missing model")
            
        prompt_tpl = self.get_prompt("Phase 4: 重點標記指令")
        if not prompt_tpl:
            self.error("❌ 找不到 prompt 指令，請確認 prompt.md 有「Phase 4: 重點標記指令」段落")
            return markdown_text  # Fallback to original
            
        chunks = smart_split(markdown_text, chunk_size)
        self.info(f"📦 [SmartHighlighter] 共 {len(chunks)} 個片段待標記 (模型: {model_name})")
        
        highlighted_parts = []
        pbar, stop_tick, t = self.create_spinner(f"標記")
        
        for idx, chunk in enumerate(chunks, 1):
            if self.stop_requested:
                self.warning("⚠️  [SmartHighlighter] 收到中止信號，停止標記")
                break
                
            if len(chunk.strip()) < min_chunk_chars:
                highlighted_parts.append(chunk)
                continue
                
            prompt = f"{prompt_tpl}\n\n【原文片段】:\n{chunk}"
            
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
                        f"   ⚠️  片段 {idx} [防竄改觸發]: LLM 輸出過短 "
                        f"({len(result.strip())} < {len(chunk) * verbatim_threshold:.0f})，還原原文"
                    )
                    highlighted_parts.append(chunk)
                else:
                    highlighted_parts.append(result.strip())
            except Exception as e:
                self.error(f"   ❌ 片段 {idx} 標記失敗: {e}，還原原文")
                highlighted_parts.append(chunk)
                
        self.finish_spinner(pbar, stop_tick, t)
        self.llm.unload_model(model_name, logger=self)
        
        return "\n\n".join(highlighted_parts)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Smart Highlighter Skill")
    parser.add_argument("--subject", default="Default", help="Subject label")
    parser.add_argument("--profile", help="Config profile override")
    args = parser.parse_args()
    
    # Read from stdin for standalone testing
    if not sys.stdin.isatty():
        input_text = sys.stdin.read()
        if input_text:
            result = SmartHighlighter(profile=args.profile).run(input_text, subject=args.subject)
            print(result)
    else:
        print("Please pipe markdown text via stdin. Example: cat doc.md | python highlight.py")
