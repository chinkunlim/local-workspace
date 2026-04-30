"""
Glossary Manager
Handles merging skill-specific local glossaries into a global priority_terms dictionary.
Also generates prompt injections for preserving protected terms during LLM synthesis.
"""

import glob
import json
import os


class GlossaryManager:
    def __init__(self, workspace_root: str, skill_name: str):
        self.workspace_root = workspace_root
        self.skill_name = skill_name

        # Determine paths specific to this skill
        self.skill_input_dir = os.path.join(self.workspace_root, "data", self.skill_name, "input")
        self.priority_terms_path = os.path.join(
            self.workspace_root, "skills", self.skill_name, "config", "priority_terms.json"
        )

    def sync_all(self, logger=None) -> int:
        """
        Scan audio-transcriber state directories for glossary.json files.
        Merge their mappings into the global priority_terms.json.
        Returns the number of new mappings added.
        """
        if not os.path.exists(self.priority_terms_path):
            if logger:
                logger.warning(f"找不到全域字彙庫路徑: {self.priority_terms_path}")
            return 0

        with open(self.priority_terms_path, encoding="utf-8") as f:
            try:
                priority_data = json.load(f)
            except json.JSONDecodeError:
                if logger:
                    logger.error("全域字彙庫格式破裂。")
                return 0

        subs = priority_data.get("CRITICAL_SUBSTITUTIONS", {})
        protection = priority_data.get("CRITICAL_TERM_PROTECTION", [])

        if not os.path.isdir(self.skill_input_dir):
            return 0

        added_count = 0
        search_pattern = os.path.join(self.skill_input_dir, "*", "glossary.json")
        for gfile in glob.glob(search_pattern):
            try:
                with open(gfile, encoding="utf-8") as f:
                    local_glossary = json.load(f)

                for wrong_term, correct_term in local_glossary.items():
                    if wrong_term not in subs:
                        subs[wrong_term] = correct_term
                        added_count += 1

                    if correct_term not in protection:
                        protection.append(correct_term)
            except Exception as e:
                if logger:
                    logger.warning(f"讀取地方字彙庫失敗 ({gfile}): {e}")

        if added_count > 0:
            priority_data["CRITICAL_SUBSTITUTIONS"] = subs
            priority_data["CRITICAL_TERM_PROTECTION"] = protection

            with open(self.priority_terms_path, "w", encoding="utf-8") as f:
                json.dump(priority_data, f, ensure_ascii=False, indent=2)
            if logger:
                logger.info(
                    f"🔄 跨模組術語同步完成！成功引入 {added_count} 個新詞彙至中央防護清單。"
                )

        return added_count

    def get_global_prompt_injection(self) -> str:
        """
        Reads the latest priority_terms.json and constructs the PROMPT injection string.
        """
        if not os.path.exists(self.priority_terms_path):
            return ""

        with open(self.priority_terms_path, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return ""

        template = data.get("PROMPT_INJECTION_TEMPLATE", "")
        protection_list = data.get("CRITICAL_TERM_PROTECTION", [])

        if not template or not protection_list:
            return ""

        # Create a comma-separated list of protected terms
        terms_str = "、".join(
            [t for t in protection_list if not t.startswith("_")]
        )  # Filter out _comment
        return template.replace("{terms}", terms_str)
