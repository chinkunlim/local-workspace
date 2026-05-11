import os
import re

mapping = {
    "cli": "cli",
    "cli_menu": "cli",
    "cli_runner": "cli",
    "cli_config_wizard": "cli",
    "check_status": "cli",
    "config_manager": "config",
    "config_validation": "config",
    "state_manager": "state",
    "state_backend": "state",
    "session_state": "state",
    "memory_updater": "state",
    "resume_manager": "state",
    "router_agent": "orchestration",
    "task_queue": "orchestration",
    "scheduler": "orchestration",
    "event_bus": "orchestration",
    "pipeline_base": "orchestration",
    "run_all_pipelines": "orchestration",
    "skill_registry": "orchestration",
    "telegram_bot": "services",
    "inbox_daemon": "services",
    "hitl_manager": "services",
    "security_manager": "services",
    "llm_client": "ai",
    "hybrid_retriever": "ai",
    "graph_store": "ai",
    "knowledge_pusher": "ai",
    "file_utils": "utils",
    "text_utils": "utils",
    "path_builder": "utils",
    "log_manager": "utils",
    "atomic_writer": "utils",
    "error_classifier": "utils",
    "bootstrap": "utils",
    "data_layout": "utils",
    "subject_manager": "utils",
    "glossary_manager": "utils",
    "diff_engine": "utils",
}


def replace_imports_in_file(filepath):
    with open(filepath) as f:
        content = f.read()

    new_content = content
    # Replace `from core.X import Y`
    for mod, submod in mapping.items():
        new_content = re.sub(
            rf"from\s+core\.{mod}\s+import", f"from core.{submod}.{mod} import", new_content
        )
        new_content = re.sub(
            rf"import\s+core\.{mod}(\s|$)", rf"import core.{submod}.{mod}\1", new_content
        )
        new_content = re.sub(
            rf"from\s+core\.{mod}(\s|$)", rf"from core.{submod}.{mod}\1", new_content
        )  # catch 'from core.utils.path_builder import *'

    if new_content != content:
        with open(filepath, "w") as f:
            f.write(new_content)


def expand_relative_imports(filepath):
    with open(filepath) as f:
        content = f.read()

    # Expand `from .X import` to `from core.X import`
    # Match `from .` followed by word characters. We need to capture the module name.
    new_content = re.sub(r"from\s+\.(\w+)\s+import", r"from core.\1 import", content)

    if new_content != content:
        with open(filepath, "w") as f:
            f.write(new_content)


for root, _, files in os.walk("/Users/limchinkun/Desktop/local-workspace/openclaw-sandbox/core"):
    if ".venv" in root or "__pycache__" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            expand_relative_imports(os.path.join(root, file))

for root, _, files in os.walk("/Users/limchinkun/Desktop/local-workspace/openclaw-sandbox"):
    if ".venv" in root or "__pycache__" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            replace_imports_in_file(os.path.join(root, file))

for root, _, files in os.walk("/Users/limchinkun/Desktop/local-workspace/infra"):
    if ".venv" in root or "__pycache__" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            replace_imports_in_file(os.path.join(root, file))
