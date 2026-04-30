import os
import re

ENTRY_POINTS = [
    ("skills/audio_transcriber/scripts/run_all.py", "Audio Transcriber"),
    ("skills/academic_edu_assistant/scripts/run_all.py", "Academic Education Assistant"),
    ("skills/knowledge_compiler/scripts/run_all.py", "Knowledge Compiler"),
    ("skills/doc_parser/scripts/run_all.py", "Doc Parser"),
    ("skills/interactive_reader/scripts/run_all.py", "Interactive Reader"),
    ("skills/note_generator/scripts/synthesize.py", "Note Generator"),
    ("skills/smart_highlighter/scripts/highlight.py", "Smart Highlighter"),
    ("skills/inbox_manager/scripts/query.py", "Inbox Manager"),
    ("skills/telegram_kb_agent/scripts/bot_daemon.py", "Telegram KB Agent"),
    ("skills/telegram_kb_agent/scripts/indexer.py", "Telegram KB Indexer"),
    ("skills/telegram_kb_agent/scripts/query.py", "Telegram KB Query"),
]

WRAPPER_TEMPLATE = """
    try:
{indented_body}
        print("🏁 Pipeline 執行完畢。")
        try:
            import subprocess
            subprocess.run(
                ["osascript", "-e", 'display notification "Pipeline 執行完畢" with title "Open-Claw"'],
                check=False,
            )
        except Exception:
            pass
    except KeyboardInterrupt:
        print("\\n🛑 使用者手動中斷執行 (KeyboardInterrupt)")
        try:
            import subprocess
            subprocess.run(
                ["osascript", "-e", 'display notification "Execution Interrupted" with title "Open-Claw"'],
                check=False,
            )
        except Exception:
            pass
        import sys
        sys.exit(130)
"""


def patch_file(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # Skip if already patched
    if "osascript" in content and "Execution Interrupted" in content:
        print(f"Already patched: {filepath}")
        return

    # Special case for audio_transcriber (we just manually patch the EXCEPT block in run())
    if "audio_transcriber" in filepath:
        if "except KeyboardInterrupt:" not in content:
            # We already patched it via multi_replace, but we reverted git.
            pass

    # Find the if __name__ == "__main__": block
    match = re.search(r'^if __name__ == "__main__":\s*\n(.*)', content, re.MULTILINE | re.DOTALL)
    if not match:
        print(f"Could not find main block in: {filepath}")
        return

    main_body = match.group(1)

    # Check if it has a try block already (if it does, maybe we shouldn't patch)
    if main_body.strip().startswith("try:"):
        print(f"Skipping {filepath}, already has a try block.")
        return

    # For each line in main_body, we add 4 spaces, since it's already at level 4.
    # Level 4 + 4 = 8, which matches the indentation of `try:`'s body.
    indented_body = "\n".join("    " + line if line else line for line in main_body.split("\n"))

    new_main_block = (
        'if __name__ == "__main__":\n'
        + WRAPPER_TEMPLATE.format(indented_body=indented_body.rstrip())
        + "\n"
    )

    new_content = content[: match.start()] + new_main_block

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Patched: {filepath}")


for filepath, name in ENTRY_POINTS:
    patch_file(filepath)
