import json
import re
from typing import Dict, List

from core.ai.llm_client import OllamaClient
from core.utils.config_manager import config_manager


class SemanticMatcher:
    """
    Semantic Matcher for finding the best corresponding reference documents
    for a given transcript using an LLM to evaluate semantic relevance.
    """

    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client

    def find_best_matches(
        self,
        transcript_text: str,
        candidate_docs: Dict[str, str],
        logger=None,
    ) -> List[str]:
        """
        Find the best matching document keys for a given transcript using LLM.

        Args:
            transcript_text: The transcript content (usually the first N characters).
            candidate_docs: A dict mapping doc_prefix -> doc_content_preview (first N characters).
            logger: Optional logger for outputting trace information.

        Returns:
            List of matching doc_prefixes.
        """
        if not candidate_docs:
            return []

        # Sort the keys to preserve sequential order
        sorted_keys = sorted(candidate_docs.keys())

        # Build prompt
        prompt = (
            "你是一個專業的課程教材比對助手。\n"
            "以下是一段上課語音逐字稿的開頭內容，以及幾份按照順序排列的講義候選清單。\n"
            "講義具有前後連貫順序（例如 L01-L04 可能對應講義 01，L05-L07 對應講義 02）。\n"
            "請根據語音內容，判斷這段語音最符合哪幾份講義。\n\n"
            "【語音逐字稿開頭】：\n"
            f"{transcript_text[:1000]}\n\n"
            "【備選講義清單】：\n"
        )

        for key in sorted_keys:
            doc_preview = candidate_docs[key][:500]
            prompt += f"--- 講義 ID: {key} ---\n{doc_preview}...\n\n"

        prompt += (
            '請嚴格只輸出一個 JSON 陣列，包含你認為最對應的講義 ID 字串，例如：["01"] 或 ["01", "02"]。\n'
            "請絕對不要輸出任何其他解釋、思考過程、或 Markdown 標籤。"
        )

        # Use router default config model, or a fallback (e.g. qwen3:8b)
        router_config = config_manager.get_router_config()
        model_name = router_config.get("model", "qwen3:8b")

        if logger:
            logger.info(f"🔍 啟動語意配對... (使用 {model_name} 比對 {len(sorted_keys)} 份講義)")

        try:
            res = self.llm.generate(model=model_name, prompt=prompt, options={"temperature": 0.0})

            res_text = res.strip()

            # Strip potential Markdown code blocks if the LLM adds them despite instructions
            if res_text.startswith("```json"):
                res_text = res_text[7:]
            if res_text.startswith("```"):
                res_text = res_text[3:]
            if res_text.endswith("```"):
                res_text = res_text[:-3]

            res_text = res_text.strip()

            # Attempt to extract JSON array if there's surrounding text
            match = re.search(r"\[.*?\]", res_text, re.DOTALL)
            if match:
                res_text = match.group(0)

            selected_ids = json.loads(res_text)

            if not isinstance(selected_ids, list):
                selected_ids = [selected_ids]

            # Convert to strings and filter out hallucinations
            valid_selections = [str(k) for k in selected_ids if str(k) in candidate_docs]

            if logger:
                logger.info(f"✅ 語意配對結果: 決定配對講義 {valid_selections}")

            # Optionally unload the model to save memory if needed,
            # but usually router models are kept alive.
            # We will let the caller decide if they want to unload.

            return valid_selections

        except Exception as e:
            if logger:
                logger.warning(
                    f"⚠️ 語意配對失敗: {e}，將回傳空清單。原始輸出: {res_text if 'res_text' in locals() else 'N/A'}"
                )
            return []
