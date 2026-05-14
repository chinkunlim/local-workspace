import os
import re

WORKSPACE = "/Users/limchinkun/Desktop/local-workspace/openclaw-sandbox"

print_files = [
    "core/services/hitl_manager.py",
    "core/services/telegram_bot.py",
    "core/services/security_manager.py",
    "core/orchestration/skill_registry.py",
    "core/orchestration/human_gate.py",
    "core/state/resume_manager.py",
    "core/utils/subject_manager.py",
    "core/ai/knowledge_pusher.py",
    "core/cli/check_status.py",
    "core/state/state_manager.py",
    "core/cli/cli_menu.py",
    "core/cli/cli_config_wizard.py",
]

for pf in print_files:
    pf_path = os.path.join(WORKSPACE, pf)
    if os.path.exists(pf_path):
        with open(pf_path, encoding="utf-8") as f:
            content = f.read()
        if "from rich import print" not in content:
            # insert after __future__ or at the top of imports
            if "from __future__ import annotations" in content:
                content = content.replace(
                    "from __future__ import annotations",
                    "from __future__ import annotations\nfrom rich import print",
                    1,
                )
            else:
                content = re.sub(
                    r"^(import |from )",
                    r"from rich import print\n\1",
                    content,
                    count=1,
                    flags=re.MULTILINE,
                )
            with open(pf_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Fixed print() in {pf}")

unload_files = [
    "skills/knowledge_compiler/scripts/phases/p02_extract_graph.py",
    "skills/student_researcher/scripts/phases/p02_synthesis.py",
    "skills/student_researcher/scripts/phases/p01_claim_extraction.py",
    "skills/doc_parser/scripts/phases/p00b_png_pipeline.py",
    "skills/feynman_simulator/scripts/phases/p02_debate_synthesis.py",
    "skills/feynman_simulator/scripts/phases/p01_feynman_debate.py",
    "skills/gemini_verifier_agent/scripts/phases/p01_ai_debate.py",
    "skills/telegram_kb_agent/scripts/bot_daemon.py",
]

for uf in unload_files:
    uf_path = os.path.join(WORKSPACE, uf)
    if os.path.exists(uf_path):
        with open(uf_path, encoding="utf-8") as f:
            content = f.read()
        if "unload_model" not in content:
            # Simple regex replace for self.llm.generate
            # Add self.llm.unload_model(self.model_name) or self.llm.unload_model(...)
            # Wait, bot_daemon.py might use llm_client
            if "self.llm.generate" in content:
                content = re.sub(
                    r"(.*self\.llm\.generate\(.*?\).*?)\n",
                    r"\1\n\g<1>".replace(r"\g<1>", "")
                    + "        if hasattr(self, 'model_name'):\n            self.llm.unload_model(self.model_name)\n        elif hasattr(self, 'model'):\n            self.llm.unload_model(self.model)\n",
                    content,
                    flags=re.DOTALL,
                )
            elif "llm_client.generate" in content:
                pass  # Need manual check for bot_daemon if it fails

            # actually doing it simpler: inject unload_model right before return in the function, or simply replacing line by line.
            # a safer way is to just replace `.generate(` with `.generate(` and then add `unload_model` manually?
            pass

print("Python script generated.")
