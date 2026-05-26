import os
import sys

from core.services.telegram_bot import send_inline_keyboard


def main():
    if len(sys.argv) < 2:
        return
    filepath = sys.argv[1]
    filename = os.path.basename(filepath)
    text = f"💡 您之前有一個好點子：\n`{filename}`\n\n現在要啟動瀏覽器開始深度研究嗎？"
    buttons = [
        [
            ("🚀 啟動研究", f"/hitl idea_approve {filepath}"),
            ("⏸️ 暫時不要", f"/hitl idea_skip {filepath}"),
        ]
    ]
    send_inline_keyboard(text, buttons)


if __name__ == "__main__":
    main()
