import os
import subprocess
import sys
import threading
import time

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core.hitl_manager import HITLManager
from core.log_manager import build_logger
from core.telegram_bot import _get_bot_config, send_inline_keyboard, send_message

_workspace_root = os.environ.get(
    "WORKSPACE_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)
# S2: Resolve canonical path — prevents symlink/env-var path traversal attack
_workspace_root = os.path.realpath(_workspace_root)

_logger = build_logger(
    "OpenClaw.BotDaemon", log_file=os.path.join(_workspace_root, "logs", "bot_daemon.log")
)

# M4: User preference store path (runtime model switching)
_USER_PREFS_PATH = os.path.join(_workspace_root, "state", "user_prefs.json")


def _load_user_prefs() -> dict:
    import json

    try:
        with open(_USER_PREFS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_user_prefs(prefs: dict) -> None:
    import json

    os.makedirs(os.path.dirname(_USER_PREFS_PATH), exist_ok=True)
    tmp = _USER_PREFS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(prefs, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _USER_PREFS_PATH)


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
                            "\U0001f680 \u6b63\u5728\u555f\u52d5 Open Claw \u6838\u5fc3\u751f\u614b\u7cfb...",
                            chat_id,
                        )
                        start_script = os.path.realpath(
                            os.path.abspath(
                                os.path.join(_workspace_root, "..", "infra", "scripts", "start.sh")
                            )
                        )
                        _infra_root = os.path.realpath(
                            os.path.abspath(os.path.join(_workspace_root, "..", "infra"))
                        )
                        # S2: Ensure script is within expected infra directory
                        if not start_script.startswith(_infra_root):
                            send_message(
                                "\u26a0\ufe0f \u5b89\u5168\u932f\u8aa4\uff1a\u555f\u52d5\u8173\u672c\u8def\u5f91\u7570\u5e38\uff0c\u5df2\u4e2d\u6b62\u3002",
                                chat_id,
                            )
                        else:
                            subprocess.Popen(["bash", start_script])
                            send_message(
                                "\u2705 \u7cfb\u7d71\u555f\u52d5\u7a0b\u5e8f\u5df2\u5728\u80cc\u666f\u57f7\u884c\u3002",
                                chat_id,
                            )

                    elif text == "/stop_system":
                        send_message(
                            "\U0001f6d1 \u6b63\u5728\u95dc\u9589 Open Claw \u6838\u5fc3\u751f\u614b\u7cfb...",
                            chat_id,
                        )
                        stop_script = os.path.realpath(
                            os.path.abspath(
                                os.path.join(_workspace_root, "..", "infra", "scripts", "stop.sh")
                            )
                        )
                        _infra_root = os.path.realpath(
                            os.path.abspath(os.path.join(_workspace_root, "..", "infra"))
                        )
                        # S2: Ensure script is within expected infra directory
                        if not stop_script.startswith(_infra_root):
                            send_message(
                                "\u26a0\ufe0f \u5b89\u5168\u932f\u8aa4\uff1a\u95dc\u9589\u8173\u672c\u8def\u5f91\u7570\u5e38\uff0c\u5df2\u4e2d\u6b62\u3002",
                                chat_id,
                            )
                        else:
                            subprocess.Popen(["bash", stop_script])
                            send_message(
                                "\u2705 \u7cfb\u7d71\u95dc\u9589\u7a0b\u5e8f\u5df2\u5728\u80cc\u666f\u57f7\u884c\uff0cOllama \u8207\u5176\u4ed6\u670d\u52d9\u5c07\u88ab\u505c\u6b62\u3002",
                                chat_id,
                            )

                    elif text.startswith("/query "):
                        q = text[7:].strip()
                        send_message(
                            f"\U0001f9e0 \u6b63\u5728\u70ba\u60a8\u67e5\u8a62\u77e5\u8b58\u5eab: {q}",
                            chat_id,
                        )

                        # A1: Run blocking query in background thread — keeps poll loop responsive
                        def _bg_query(question=q, cid=chat_id):
                            ans = run_query(question)
                            send_message(ans, cid)

                        threading.Thread(target=_bg_query, daemon=True).start()

                    elif text.startswith("/model"):
                        # M4: Runtime LLM model switching
                        arg = text[6:].strip()
                        if arg:
                            prefs = _load_user_prefs()
                            prefs["active_model"] = arg
                            _save_user_prefs(prefs)
                            send_message(
                                f"\u2705 \u6a21\u578b\u5df2\u5207\u63db\u70ba `{arg}`\uff0c\u4e0b\u6b21\u4efb\u52d9\u751f\u6548\u3002",
                                chat_id,
                            )
                        else:
                            prefs = _load_user_prefs()
                            current = prefs.get(
                                "active_model",
                                "(\u672a\u8a2d\u5b9a\uff0c\u4f7f\u7528\u5404 Skill \u9810\u8a2d\u6a21\u578b)",
                            )
                            send_message(
                                f"\U0001f916 \u76ee\u524d\u6a21\u578b: `{current}`", chat_id
                            )

                    elif text.startswith("/hitl "):
                        # H2: HITL callback — /hitl approve|skip <trace_id>
                        parts = text.split()
                        if len(parts) >= 3:
                            resolution = parts[1].lower()
                            trace_id = parts[2]
                            hitl_mgr = HITLManager(base_dir=_workspace_root)
                            snapshot = hitl_mgr.resolve(trace_id, resolution)
                            if snapshot is not None:
                                send_message(
                                    f"\u2705 HITL \u5df2\u8655\u7406: `{trace_id}`\n\u6c7a\u5b9a: {resolution}\n\u7ba1\u7dda\u5c07\u81ea\u52d5\u6062\u5fa9\u3002",
                                    chat_id,
                                )
                            else:
                                send_message(
                                    f"\u26a0\ufe0f \u627e\u4e0d\u5230 HITL \u4e8b\u4ef6 `{trace_id}`\uff0c\u53ef\u80fd\u5df2\u8655\u7406\u3002",
                                    chat_id,
                                )
                        else:
                            send_message("\u7528\u6cd5: /hitl approve|skip <trace_id>", chat_id)

                    elif text == "/start" or text == "/help":
                        send_message(
                            "\U0001f44b \u6b61\u8fce\u4f7f\u7528 Open Claw \u5168\u80fd\u9059\u63a7\u4e2d\u6a1e\uff01\n\n"
                            "[\u9032\u5ea6\u7ba1\u7406]\n"
                            "/status - \u67e5\u770b\u7cfb\u7d71\u8655\u7406\u4f47\u5217\u9032\u5ea6\n"
                            "/run \u6216 /resume - \u4f9d\u5e8f\u57f7\u884c\u5f85\u8fa6\u4efb\u52d9\n"
                            "/pause - \u66ab\u505c\u57f7\u884c\u4e26\u91cb\u653e\u6240\u6709\u8a18\u61b6\u9ad4\n\n"
                            "[\u7cfb\u7d71\u7ba1\u7406]\n"
                            "/start_system - \u958b\u555f\u6574\u500b\u751f\u614b\u7cfb\u5c08\u6848\n"
                            "/stop_system - \u95dc\u9589\u6574\u500b\u751f\u614b\u7cfb\u5c08\u6848 (\u4e0d\u542b Bot)\n\n"
                            "[\u77e5\u8b58\u554f\u7b54]\n"
                            "/query <\u554f\u984c> - \u5728\u77e5\u8b58\u5eab\u4e2d\u767c\u554f\n\n"
                            "[\u6a21\u578b\u7ba1\u7406]\n"
                            "/model <\u540d\u7a31> - \u5207\u63db LLM \u6a21\u578b (\u7a7a\u767d = \u67e5\u8a62\u76ee\u524d)\n\n"
                            "[HITL \u4ecb\u5165]\n"
                            "/hitl approve|skip <trace_id> - \u56de\u61c9\u7cfb\u7d71\u66ab\u505c\u7684\u4ecb\u5165\u4e8b\u4ef6",
                            chat_id,
                        )

        except requests.exceptions.RequestException:
            # Network issue, retry silently
            time.sleep(5)
        except Exception as e:
            _logger.error("❌ [BotDaemon] 未知錯誤: %s", e, exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    try:
        main()
        print("🏁 Pipeline 執行完畢。")
        try:
            import subprocess

            subprocess.run(
                [
                    "osascript",
                    "-e",
                    'display notification "Pipeline 執行完畢" with title "Open-Claw"',
                ],
                check=False,
            )
        except Exception:
            pass
    except KeyboardInterrupt:
        print("\n🛑 使用者手動中斷執行 (KeyboardInterrupt)")
        try:
            import subprocess

            subprocess.run(
                [
                    "osascript",
                    "-e",
                    'display notification "Execution Interrupted" with title "Open-Claw"',
                ],
                check=False,
            )
        except Exception:
            pass
        import sys

        sys.exit(130)
