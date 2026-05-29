import json
import os
import sys

# Core Bootstrap
from core.orchestration.event_bus import DomainEvent, EventBus
from core.orchestration.pipeline_base import PipelineBase as PhaseBase
from core.utils.atomic_writer import AtomicWriter
from skills.note_generator.scripts.run_all import strip_think_tags


class Phase2Synthesis(PhaseBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="p02_synthesis",
            phase_name="Final Synthesis and APA Output",
            skill_name="student_researcher",
        )

    def run(self, force: bool = False, **kwargs) -> None:
        input_dir = self.dirs["inbox"]
        semantic_ctx_path = os.path.join(self.base_dir, "state", "semantic_context.json")
        semantic_ctx = {}
        if os.path.exists(semantic_ctx_path):
            try:
                with open(semantic_ctx_path, encoding="utf-8") as f:
                    semantic_ctx = json.load(f)
            except Exception:
                pass

        for root, _, files in os.walk(input_dir):
            for file in files:
                if not file.endswith(".json"):
                    continue

                filepath = os.path.join(root, file)
                self.info(f"📂 處理查證完成檔案: {file}")

                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)

                source_md_path = data.get("source_md")
                debated_claims = data.get("debated_claims", [])

                if not source_md_path or not os.path.exists(source_md_path):
                    self.error(f"❌ 找不到原始筆記檔案: {source_md_path}")
                    continue

                with open(source_md_path, encoding="utf-8") as f:
                    original_note = f.read()

                # Load all debate archives
                debate_texts = []
                for idx, claim_data in enumerate(debated_claims):
                    archive_path = claim_data.get("debate_archive")
                    if archive_path and os.path.exists(archive_path):
                        with open(archive_path, encoding="utf-8") as f:
                            debate_texts.append(f"【討論紀錄 {idx + 1}】\n" + f.read())

                if not debate_texts:
                    self.warning("⚠️ 沒有查證到任何有效討論紀錄，直接輸出原檔案。")
                    out_path = os.path.splitext(filepath)[0] + "_research.md"
                    AtomicWriter.write_text(out_path, original_note)
                    continue

                all_debates = "\n\n".join(debate_texts)

                parts = os.path.normpath(source_md_path).split(os.sep)
                subj = parts[-2] if len(parts) >= 2 else "Default"
                fname = parts[-1] if len(parts) >= 1 else os.path.basename(source_md_path)
                ctx_key = f"{subj}/{fname}"
                ctx = semantic_ctx.get(ctx_key, {})
                related_files = ctx.get("related_files", [])
                new_tags = ctx.get("new_tags", [])
                is_orphan = ctx.get("is_orphan", False)

                semantic_instructions = ""
                if is_orphan and new_tags:
                    semantic_instructions = f"6. [特別指示] 這是一個全新的靈感點子，請在文末強制加上以下標籤 (Hashtags) 以放入孵化器 (Incubator)：{', '.join(new_tags)}\n"
                elif related_files:
                    semantic_instructions = f"6. [特別指示] 系統在舊有知識庫中發現這篇對話與以下檔案高度相關：{', '.join(related_files)}。請你在總結時，強制在關鍵名詞處插入對應 Obsidian 雙向連結 (例如 [[{related_files[0]}]])。\n"

                prompt = (
                    "請扮演一位嚴謹的研究助理。你現在有一份「原始點子/筆記」與數份「AI 文獻查證討論紀錄」。\n"
                    "這是一份『延伸研究報告 (Academic Extension Document)』，請不要改寫原始筆記，而是針對原始內容中被探討的論點進行延伸擴充與總結。\n"
                    "要求：\n"
                    "1. 開頭請寫一小段摘要，說明這份延伸研究的核心發現。\n"
                    "2. 必須在文中加入 APA 格式的引用標記 (Author, Year)。\n"
                    "3. 在文末建立 `## References` 區塊，列出所有參考文獻 (APA 格式)。\n"
                    "4. 為了 Obsidian 知識庫整合，請在重要的專有名詞加上 `[[雙向連結]]`，並在文末加上相關的 `#tag`。\n"
                    "5. 如果討論紀錄中有附上 Local Evidence Link，請在 References 中加上該檔案連結，例如 `[[Local Evidence Link]]`。\n"
                    f"{semantic_instructions}\n"
                    f"【原始點子/筆記】:\n{original_note}\n\n"
                    f"【AI 文獻查證討論紀錄】:\n{all_debates}\n\n"
                    "請直接輸出完整的 Markdown 延伸報告內容。"
                )

                self.info("✍️  正在綜合學習與生成最終筆記...")
                try:
                    # primary: deepseek-r1:8b (CoT synthesis); fallback: qwen3:8b (via config.yaml)
                    final_note = self.llm.generate(model="deepseek-r1:8b", prompt=prompt)
                    final_note = strip_think_tags(final_note)
                    self.llm.unload_model("deepseek-r1:8b")
                except Exception as e:
                    self.error(f"❌ 生成失敗: {e}")
                    continue

                out_path = os.path.splitext(filepath)[0] + "_research.md"
                AtomicWriter.write_text(out_path, final_note)

                self.info(f"✅ 最終筆記生成完成: {out_path}")

                # Emit PipelineCompleted to trigger knowledge_compiler
                target_subj = "Incubator" if is_orphan else kwargs.get("subject", subj)
                self.emit_completed(
                    out_path, target_subj, chain=["student_researcher", "knowledge_compiler"]
                )

        self.state_manager.sync_physical_files()
