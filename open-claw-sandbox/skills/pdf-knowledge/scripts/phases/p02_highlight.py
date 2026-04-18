# -*- coding: utf-8 -*-
"""
p02_highlight.py — Phase 2: 重點標記 (Anti-Tampering)
======================================================
從 01_Processed/<subject>/<pdf_id>/raw_extracted.md 讀取原文，
使用 LLM 以 **bold**、==highlight==、`code` 等 Markdown 標記標注重點，
絕不刪除或改寫任何文字（Anti-Tampering 防竄改機制）。

輸出：02_Highlighted/<subject>/<pdf_id>/highlighted.md

設計參考：skills/voice-memo/scripts/phases/p04_highlight.py
"""

import os
import sys

# Internal Core Bootstrap
from core.bootstrap import ensure_core_path as _bootstrap
_bootstrap(__file__)

from core import PipelineBase, AtomicWriter
from core.text_utils import smart_split


class Phase2Highlight(PipelineBase):
    """
    Phase 2: 重點標記 (Anti-Tampering).

    Reads raw_extracted.md from 01_Processed, applies Markdown highlight/bold
    annotations to key concepts via LLM, and writes highlighted.md to
    02_Highlighted. The source text is NEVER modified — only annotations are added.

    The verbatim_threshold guard ensures the LLM cannot delete content:
    if the output is shorter than threshold * input length, the original
    chunk is used unchanged.
    """

    # Fallback threshold if not set in config.yaml
    DEFAULT_VERBATIM_THRESHOLD: float = 0.50

    def __init__(self) -> None:
        super().__init__(
            phase_key="phase2",
            phase_name="重點標記",
            skill_name="pdf-knowledge",
        )
        config = self.get_config("phase2")
        self.highlight_model: str = config.get("model", "")
        self.highlight_options: dict = config.get("options", {})
        self.chunk_size: int = int(config.get("chunk_size", 6000))
        self.verbatim_threshold: float = float(
            config.get("verbatim_threshold", self.DEFAULT_VERBATIM_THRESHOLD)
        )
        self.min_chunk_chars: int = int(config.get("min_chunk_chars", 30))
        if not self.highlight_model:
            raise RuntimeError("pdf-knowledge phase2 config missing model")

    def run(self, subject: str, filename: str) -> bool:
        """
        Highlight key points in raw_extracted.md for one PDF.

        Args:
            subject: Subject folder the PDF belongs to.
            filename: The PDF filename.

        Returns:
            True on success, False on failure.
        """
        pdf_id = os.path.splitext(filename)[0]
        self.info(f"🖊️  [Phase 2] 啟動重點標記: [{subject}] {pdf_id}")

        # ── Paths ──────────────────────────────────────────────────────────
        raw_path = os.path.join(self.dirs["processed"], subject, pdf_id, "raw_extracted.md")
        out_dir = os.path.join(self.dirs["highlighted"], subject, pdf_id)
        out_path = os.path.join(out_dir, "highlighted.md")

        if not os.path.exists(raw_path):
            self.warning(f"⚠️  [Phase 2] 找不到 raw_extracted.md，跳過: {raw_path}")
            return False

        os.makedirs(out_dir, exist_ok=True)

        # ── Read source ────────────────────────────────────────────────────
        with open(raw_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        self.info(f"📖 [Phase 2] 原文長度 {len(raw_text):,} 字元，分塊大小 {self.chunk_size:,} (模型: {self.highlight_model})")

        # ── Load prompt ────────────────────────────────────────────────────
        prompt_tpl = self.get_prompt("Phase 2: 重點標記指令")
        if not prompt_tpl:
            self.error("❌ [Phase 2] 找不到 prompt 指令，請確認 prompt.md 有「Phase 2: 重點標記指令」段落")
            return False

        # ── Chunked LLM processing ─────────────────────────────────────────
        chunks = smart_split(raw_text, self.chunk_size)
        self.info(f"📦 [Phase 2] 共 {len(chunks)} 個片段待標記")

        highlighted_parts = []
        for idx, chunk in enumerate(chunks, 1):
            if self.stop_requested:
                self.warning("⚠️  [Phase 2] 收到中止信號，停止標記")
                break

            if len(chunk.strip()) < self.min_chunk_chars:
                highlighted_parts.append(chunk)
                continue

            self.info(f"   🖊️  [{idx}/{len(chunks)}] 標記中...")
            prompt = f"{prompt_tpl}\n\n【原文片段】:\n{chunk}"

            try:
                result = self.llm.generate(
                    model=self.highlight_model,
                    prompt=prompt,
                    options=self.highlight_options,
                    logger=self,
                )
                # Anti-Tampering guard: if output is too short, use original
                if len(result.strip()) < len(chunk) * self.verbatim_threshold:
                    self.warning(
                        f"   ⚠️  片段 {idx} [防竄改觸發]: LLM 輸出過短 "
                        f"({len(result.strip())} < {len(chunk) * self.verbatim_threshold:.0f})，還原原文"
                    )
                    highlighted_parts.append(chunk)
                else:
                    highlighted_parts.append(result.strip())
            except Exception as e:
                self.error(f"   ❌ 片段 {idx} 標記失敗: {e}，還原原文")
                highlighted_parts.append(chunk)

        # ── Write output ───────────────────────────────────────────────────
        final_doc = "\n\n".join(highlighted_parts)
        header = (
            f"<!-- highlighted.md — Phase 2 重點標記\n"
            f"     pdf_id : {pdf_id}\n"
            f"     subject: {subject}\n"
            f"     model  : {self.highlight_model}\n"
            f"     chunks : {len(chunks)}\n"
            "-->\n\n"
        )
        AtomicWriter.write_text(out_path, header + final_doc)
        self.info(f"✅ [Phase 2] 重點標記完成: {out_path} ({len(final_doc):,} 字元)")

        self.llm.unload_model(self.highlight_model, logger=self)
        return True


# ---------------------------------------------------------------------------- #
#  CLI Entry Point                                                              #
# ---------------------------------------------------------------------------- #

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 2: PDF Highlight Key Points")
    parser.add_argument("pdf", help="The PDF path")
    args = parser.parse_args()

    filename = os.path.basename(args.pdf)
    success = Phase2Highlight().run(args.subject, filename)
    sys.exit(0 if success else 1)
