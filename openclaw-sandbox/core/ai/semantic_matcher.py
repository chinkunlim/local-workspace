import json
import re
from typing import Dict, List

from core.ai.llm_client import OllamaClient


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
        target_prefix: str = None,
        logger=None,
    ) -> List[str]:
        """
        Find the best matching document keys for a given transcript using LLM.

        Args:
            transcript_text: The transcript content (usually the first N characters).
            candidate_docs: A dict mapping doc_prefix -> doc_content_preview (first N characters).
            target_prefix: The prefix of the source audio (e.g., 'L15'). Used to prevent mismatched pairs.
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
            f"{transcript_text[:3000]}\n\n"
            "【備選講義清單】：\n"
        )

        for key in sorted_keys:
            doc_preview = candidate_docs[key][:1500]
            prompt += f"--- 講義 ID: {key} ---\n{doc_preview}...\n\n"

        prefix_hint = ""
        if target_prefix:
            prefix_hint = f"3. 【重要】：語音前綴為「{target_prefix}」。請注意，同一份講義可能連續使用多週（例如 L07 講義在 L09 繼續用）。請完全以「內容語意重疊度」判斷，若內容相符，即使前綴不同也請大膽配對。\n"

        prompt += (
            "【重要注意事項】：\n"
            "1. 一段語音通常最多對應 1-2 份講義，請找出最相關的。\n"
            "2. 語音開頭可能包含行政閒聊，請耐心尋找其中的「學術專有名詞」或「課程主題」，並與講義預覽內容比對。\n"
            f"{prefix_hint}"
            "只要語音中出現的主題與備選講義內容有明顯重疊，即可將該講義 ID 納入。\n\n"
            '請嚴格只輸出一個 JSON 陣列，包含你認為最對應的講義 ID 字串，例如：["講義A"] 或 ["講義A", "講義B"]，若皆不符合請輸出 []。\n'
            "請絕對不要輸出任何其他解釋、思考過程、或 Markdown 標籤。"
        )

        # Use the fallback model configured in the LLM client
        model_name = getattr(self.llm, "fallback_model", None) or "qwen3:8b"

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

            if logger:
                logger.info(f"💡 LLM 原始配對結果 (未過濾): {selected_ids}")

            valid_selections_set = set()
            for k in selected_ids:
                k_str = str(k).strip()
                if k_str in candidate_docs:
                    valid_selections_set.add(k_str)
                else:
                    # Fallback to partial match if LLM abbreviated the ID
                    for doc_key in candidate_docs:
                        if k_str in doc_key or doc_key in k_str:
                            valid_selections_set.add(doc_key)
                            break
            valid_selections = list(valid_selections_set)

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
