"""
Phase 2: Debate Synthesis → Enriched Note
==========================================
Reads the JSON pointer written by Phase 1, loads the debate archive,
and uses the local LLM to produce an enriched version of the original
note with the following additions:

- Corrected explanations from the Tutor's Socratic challenges
- Blind spot callout boxes (> [!NOTE])
- APA-style in-text citations where claims were verified
- Obsidian WikiLinks for key concepts surfaced in the debate
- Tags: #feynman #verified
"""

from __future__ import annotations

import json
import os

from core.ai.llm_client import OllamaClient
from core.orchestration.pipeline_base import PipelineBase as PhaseBase
from core.utils.atomic_writer import AtomicWriter

_SYNTHESIS_MODEL = "qwen3:8b"  # fallback


class Phase2DebateSynthesis(PhaseBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="p02_debate_synthesis",
            phase_name="Feynman Debate Synthesis → Enriched Note",
            skill_name="feynman_simulator",
        )
        self._llm = OllamaClient()

    def run(self, force: bool = False, **kwargs) -> None:
        input_dir = self.dirs["output"]  # Phase 1 outputs are our inputs
        enriched_dir = os.path.join(self.base_dir, "enriched")
        os.makedirs(enriched_dir, exist_ok=True)

        for root, _, files in os.walk(input_dir):
            for fname in sorted(files):
                if not fname.endswith("_debate.json"):
                    continue

                pointer_path = os.path.join(root, fname)
                with open(pointer_path, encoding="utf-8") as f:
                    pointer = json.load(f)

                source_note = pointer.get("source_note", "")
                archive_path = pointer.get("debate_archive", "")

                if not os.path.exists(source_note) or not os.path.exists(archive_path):
                    self.warning(f"  ⚠️  缺少原始筆記或辯證檔案，跳過: {fname}")
                    continue

                with open(source_note, encoding="utf-8") as f:
                    original_note = f.read()

                with open(archive_path, encoding="utf-8") as f:
                    debate_text = f.read()

                self.info(f"\n📝 合成筆記: {os.path.basename(source_note)}")

                prompt = (
                    "你是一位嚴謹的大學生，剛完成了一場費曼辯證學習。\n"
                    "請根據「辯證紀錄」對「原始筆記」進行升級改寫，要求如下：\n\n"
                    "1. **保留原始筆記的完整架構**，不要刪減原有內容。\n"
                    "2. **插入「辯證盲點」區塊**：使用 `> [!CAUTION]` callout 標出最初的錯誤理解。\n"
                    "3. **插入「深化理解」區塊**：用 `> [!TIP]` callout 整合從辯證中獲得的新理解。\n"
                    "4. **重要概念**加上 `[[Obsidian WikiLink]]` 格式的雙向連結。\n"
                    "5. 在文末加上 `#feynman #verified` 標籤。\n"
                    "6. 如果辯證中有引用具體學術主張，在文末 `## References` 加上 APA 格式佔位符：\n"
                    "   `(Author, Year) — 待 academic_library_agent 補充完整 DOI`\n\n"
                    f"【原始筆記】\n{original_note}\n\n"
                    f"【辯證紀錄】\n{debate_text[:6000]}\n\n"
                    "請直接輸出完整的升級版 Markdown 筆記。"
                )

                try:
                    enriched_note = self._llm.generate(model=_SYNTHESIS_MODEL, prompt=prompt)
                except Exception as exc:
                    self.error(f"  ❌ LLM 生成失敗: {exc}")
                    continue

                out_name = os.path.basename(source_note).replace(".md", "_feynman.md")
                out_path = os.path.join(enriched_dir, out_name)
                AtomicWriter.write_text(out_path, enriched_note)

                self.info(f"  ✅ 升級筆記已輸出: {out_path}")

        self.state_manager.sync_physical_files()
