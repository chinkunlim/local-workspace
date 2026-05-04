import json
import os
import uuid

from core import PhaseBase
from core.ai.llm_client import OllamaClient


class Phase1ClaimExtraction(PhaseBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="p01_claim_extraction",
            phase_name="Claim Extraction",
            skill_name="student_researcher",
        )
        self.llm = OllamaClient()

    def run(self, force: bool = False, **kwargs) -> None:
        input_dir = self.phase_dirs["input"]

        for root, _, files in os.walk(input_dir):
            for file in files:
                if not file.endswith(".md"):
                    continue

                filepath = os.path.join(root, file)
                print(f"\n📂 處理筆記檔案: {file}")

                with open(filepath, encoding="utf-8") as f:
                    content = f.read()

                prompt = (
                    "請扮演一位嚴謹的大學生。閱讀以下筆記內容，並挑選出 1 到 3 個「最需要學術文獻佐證」的核心論點 (Claims)。\n"
                    "請以 JSON 陣列格式輸出，每個物件包含：\n"
                    "- id: 唯一的字串 ID\n"
                    "- claim: 論點的詳細描述\n"
                    "- search_query: 用來在 ScienceDirect 搜尋的精確英文關鍵字\n\n"
                    f"筆記內容:\n{content}\n\n"
                    "只輸出 JSON 陣列，不要有其他文字。"
                )

                print("🧠 正在萃取需查證之論點...")
                try:
                    response = self.llm.generate(model="deepseek-r1:8b"  # primary; fallback to qwen3:8b via config, prompt=prompt)

                    # Clean up JSON
                    start_idx = response.find("[")
                    end_idx = response.rfind("]") + 1
                    if start_idx != -1 and end_idx != -1:
                        json_str = response[start_idx:end_idx]
                        claims = json.loads(json_str)
                    else:
                        raise ValueError("No JSON array found in LLM response.")

                except Exception as e:
                    print(f"❌ 萃取失敗: {e}")
                    continue

                out_path = self._get_output_path(filepath, ext=".json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {"source_md": filepath, "claims": claims}, f, ensure_ascii=False, indent=2
                    )

                print(f"✅ 萃取完成，共 {len(claims)} 個論點，輸出至: {out_path}")

        self.state_manager.sync_physical_files()
