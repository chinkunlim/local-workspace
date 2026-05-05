import json
import os
import uuid

from core.ai.llm_client import OllamaClient
from core.orchestration.event_bus import DomainEvent, EventBus
from core.orchestration.pipeline_base import PipelineBase as PhaseBase


class Phase2Synthesis(PhaseBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="p02_synthesis",
            phase_name="Final Synthesis and APA Output",
            skill_name="student_researcher",
        )
        self.llm = OllamaClient()

    def run(self, force: bool = False, **kwargs) -> None:
        input_dir = self.dirs["input"]

        for root, _, files in os.walk(input_dir):
            for file in files:
                if not file.endswith(".json"):
                    continue

                filepath = os.path.join(root, file)
                print(f"\n📂 處理查證完成檔案: {file}")

                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)

                source_md_path = data.get("source_md")
                debated_claims = data.get("debated_claims", [])

                if not source_md_path or not os.path.exists(source_md_path):
                    print(f"❌ 找不到原始筆記檔案: {source_md_path}")
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
                    print("⚠️ 沒有查證到任何有效討論紀錄，直接輸出原檔案。")
                    out_path = os.path.splitext(filepath)[0] + ".md"
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(original_note)
                    continue

                all_debates = "\n\n".join(debate_texts)

                prompt = (
                    "請扮演一位嚴謹的大學生。你現在有一份「原始筆記」與數份「AI 文獻查證討論紀錄」。\n"
                    "請重新改寫原始筆記，將查證過程中的「新發現、證據、補充說明」融入筆記中，使內容更加紮實。\n"
                    "要求：\n"
                    "1. 必須在文中加入 APA 格式的引用標記 (Author, Year)。\n"
                    "2. 在文末建立 `## References` 區塊，列出所有參考文獻 (APA 格式)。\n"
                    "3. 為了 Obsidian 知識庫整合，請在重要的專有名詞加上 `[[雙向連結]]`，並在文末加上相關的 `#tag`。\n"
                    "4. 如果討論紀錄中有附上 Local Evidence Link，請在 References 中加上該檔案連結，例如 `[[Local Evidence Link]]`。\n\n"
                    f"【原始筆記】:\n{original_note}\n\n"
                    f"【AI 文獻查證討論紀錄】:\n{all_debates}\n\n"
                    "請直接輸出完整的 Markdown 筆記內容。"
                )

                print("✍️  正在綜合學習與生成最終筆記...")
                try:
                    # primary: deepseek-r1:8b (CoT synthesis); fallback: qwen3:8b (via config.yaml)
                    final_note = self.llm.generate(model="deepseek-r1:8b", prompt=prompt)
                except Exception as e:
                    print(f"❌ 生成失敗: {e}")
                    continue

                out_path = os.path.splitext(filepath)[0] + ".md"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(final_note)

                print(f"✅ 最終筆記生成完成: {out_path}")

                # Emit PipelineCompleted to trigger knowledge_compiler
                EventBus.publish(
                    DomainEvent(
                        name="PipelineCompleted",
                        source_skill="student_researcher",
                        payload={
                            "filepath": out_path,
                            "subject": kwargs.get("subject", "Default"),
                            "chain": [
                                "student_researcher",
                                "knowledge_compiler",
                            ],  # handoff to compiler
                        },
                    )
                )

        self.state_manager.sync_physical_files()
