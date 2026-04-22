import os
import subprocess
import sys
import time

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core.log_manager import build_logger
from core.telegram_bot import _get_bot_config, send_message

_workspace_root = os.environ.get(
    "WORKSPACE_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)
_logger = build_logger(
    "OpenClaw.BotDaemon", log_file=os.path.join(_workspace_root, "logs", "bot_daemon.log")
)


def run_status_check() -> str:
    # Run full system status check via check_status.py
    status_script = os.path.join(_workspace_root, "core", "check_status.py")
    try:
        # Popen to capture stdout
        result = subprocess.run(
            [sys.executable, status_script], capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip()
        if not output:
            output = "系統狀態為空。"
        return output
    except Exception as e:
        return f"讀取狀態失敗: {e}"


def run_query(question: str) -> str:
    query_script = os.path.join(
        _workspace_root, "skills", "telegram-kb-agent", "scripts", "query.py"
    )
    try:
        result = subprocess.run(
            [sys.executable, query_script, "--query", question],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"查詢發生錯誤: {e}"


def main():
    token, allowed_users = _get_bot_config()
    if not token:
        _logger.error("❌ [BotDaemon] 未設定 Token，機器人服務中止。請至 config.yaml 設定。")
        sys.exit(1)

    _logger.info("🤖 [BotDaemon] 機器人啟動中，監聽用戶: %s", allowed_users)

    offset = 0
    url = f"https://api.telegram.org/bot{token}/getUpdates"

    while True:
        try:
            resp = requests.get(url, params={"offset": offset, "timeout": 30}, timeout=40)
            if resp.ok:
                data = resp.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    chat_id = str(msg.get("chat", {}).get("id", ""))
                    text = msg.get("text", "").strip()

                    # Security check
                    if chat_id not in allowed_users:
                        continue

                    if text.startswith("/status"):
                        send_message("🔍 正在查詢目前系統佇列狀態...", chat_id)
                        status_text = run_status_check()
                        send_message(f"📊 【系統狀態】\n\n{status_text}", chat_id)

                    elif text == "/run" or text == "/resume":
                        send_message("⚙️ 正在背景啟動管線處理任務...", chat_id)
                        run_script = os.path.join(_workspace_root, "core", "run_all_pipelines.py")
                        subprocess.Popen([sys.executable, run_script])
                        send_message("✅ 任務已加入執行列，使用 /status 隨時查詢進度。", chat_id)

                    elif text == "/pause":
                        send_message("⏸️ 正在暫停管線並釋放記憶體...", chat_id)
                        # 發送 SIGTERM (15) 給所有相關行程，觸發優雅暫停與斷點存檔
                        subprocess.run(
                            ["pkill", "-15", "-f", "core/run_all_pipelines.py"], check=False
                        )
                        subprocess.run(
                            ["pkill", "-15", "-f", "doc-parser/scripts/run_all.py"], check=False
                        )
                        subprocess.run(
                            ["pkill", "-15", "-f", "audio-transcriber/scripts/run_all.py"],
                            check=False,
                        )
                        send_message(
                            "✅ 系統已發送暫停訊號！任務將在建立斷點後結束，記憶體隨即釋放。",
                            chat_id,
                        )

                    elif text == "/start_system":
                        send_message(
                            "🚀 正在啟動 Open Claw 核心生態系 (這可能需要幾分鐘)...", chat_id
                        )
                        start_script = os.path.abspath(
                            os.path.join(_workspace_root, "..", "infra", "scripts", "start.sh")
                        )
                        subprocess.Popen(["bash", start_script])
                        send_message("✅ 系統啟動程序已在背景執行。", chat_id)

                    elif text == "/stop_system":
                        send_message("🛑 正在關閉 Open Claw 核心生態系...", chat_id)
                        stop_script = os.path.abspath(
                            os.path.join(_workspace_root, "..", "infra", "scripts", "stop.sh")
                        )
                        subprocess.Popen(["bash", stop_script])
                        send_message(
                            "✅ 系統關閉程序已在背景執行，Ollama 與其他服務將被停止。", chat_id
                        )

                    elif text.startswith("/query "):
                        q = text[7:].strip()
                        send_message(f"🧠 正在為您查詢知識庫: {q}", chat_id)
                        ans = run_query(q)
                        send_message(ans, chat_id)

                    elif text == "/start" or text == "/help":
                        send_message(
                            "👋 歡迎使用 Open Claw 全能遙控中樞！\n\n"
                            "【進度管理】\n"
                            "/status - 查看系統處理佇列進度\n"
                            "/run 或 /resume - 依序執行待辦任務\n"
                            "/pause - 暫停執行並釋放所有記憶體\n\n"
                            "【系統管理】\n"
                            "/start_system - 開啟整個生態系專案 (啟動 WebUI/Ollama 等)\n"
                            "/stop_system - 關閉整個生態系專案 (不含 Bot)\n\n"
                            "【知識問答】\n"
                            "/query <問題> - 在知識庫中發問",
                            chat_id,
                        )

        except requests.exceptions.RequestException:
            # Network issue, retry silently
            time.sleep(5)
        except Exception as e:
            _logger.error("❌ [BotDaemon] 未知錯誤: %s", e, exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
