import os
import subprocess
import sys
import threading
import time

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core.services.hitl_manager import HITLManager
from core.services.telegram_bot import _get_bot_config, send_inline_keyboard, send_message
from core.utils.log_manager import build_logger
from core.utils.atomic_writer import AtomicWriter

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
    AtomicWriter.write_json(_USER_PREFS_PATH, prefs)


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
        _workspace_root, "skills", "telegram_kb_agent", "scripts", "query.py"
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

                    # ── P1-5: Multimodal routing ───────────────────────────────────
                    # Handle voice/audio → route to audio_transcriber inbox
                    if msg.get("voice") or msg.get("audio"):

                        def _handle_voice(_msg=msg, _cid=chat_id):
                            try:
                                from core.services.telegram_bot import download_voice

                                raw_inbox = os.path.join(_workspace_root, "data", "raw", "Telegram")
                                local_path = download_voice(_msg, raw_inbox)
                                send_message(
                                    f"\U0001f3a4 \u8a9e\u97f3\u6a94\u6848\u5df2\u63a5\u6536\uff0c\u6b63\u5728\u6392\u961f\u8f49\u9304\u4e2d...\n"
                                    f"\U0001f4c4 `{os.path.basename(local_path)}`",
                                    _cid,
                                )
                                # SystemInboxDaemon will pick it up via watchdog or next scan
                                from core.services.inbox_daemon import SystemInboxDaemon

                                SystemInboxDaemon()._process_file(local_path)
                            except Exception as _exc:
                                send_message(
                                    f"\u274c \u8a9e\u97f3\u8655\u7406\u5931\u6557: {_exc}", _cid
                                )

                        threading.Thread(target=_handle_voice, daemon=True).start()
                        continue

                    # Handle video → route to video_ingester inbox
                    if msg.get("video") or (
                        msg.get("document")
                        and msg["document"].get("mime_type", "").startswith("video/")
                    ):

                        def _handle_video(_msg=msg, _cid=chat_id):
                            try:
                                from core.services.telegram_bot import download_file

                                file_id = _msg.get("video", {}).get("file_id")
                                if not file_id:
                                    file_id = _msg.get("document", {}).get("file_id")
                                raw_inbox = os.path.join(_workspace_root, "data", "raw", "Telegram")
                                local_path = download_file(file_id, raw_inbox)
                                send_message(
                                    f"🎬 影片檔案已接收，正在排隊抽取關鍵影格與轉錄...\n"
                                    f"📄 `{os.path.basename(local_path)}`",
                                    _cid,
                                )
                                from core.services.inbox_daemon import SystemInboxDaemon

                                SystemInboxDaemon()._process_file(local_path)
                            except Exception as _exc:
                                send_message(f"❌ 影片處理失敗: {_exc}", _cid)

                        threading.Thread(target=_handle_video, daemon=True).start()
                        continue

                    # Handle photo → run inline VLM analysis and reply
                    if msg.get("photo"):

                        def _handle_photo(_msg=msg, _cid=chat_id):
                            try:
                                from core.services.telegram_bot import download_file

                                # Largest photo is last in the array
                                file_id = _msg["photo"][-1]["file_id"]
                                tmp_dir = os.path.join(_workspace_root, "data", "raw", "_photo_tmp")
                                local_path = download_file(file_id, tmp_dir)
                                send_message(
                                    "\U0001f5bc\ufe0f \u7167\u7247\u5df2\u63a5\u6536\uff0c\u6b63\u5728\u547c\u53eb\u8996\u8986\u6a21\u578b\u5206\u6790...",
                                    _cid,
                                )
                                # Encode and call VLM via OllamaClient
                                import json as _json

                                from core.ai.llm_client import OllamaClient
                                from core.utils.file_utils import encode_image_b64

                                with open(
                                    os.path.expanduser("~/.openclaw/openclaw.json"),
                                    encoding="utf-8",
                                ) as _f:
                                    _cfg = _json.load(_f)
                                _ollama_url = (
                                    _cfg.get("runtime", {})
                                    .get("ollama", {})
                                    .get("api_url", "http://127.0.0.1:11434/api")
                                )
                                _vlm_model = _cfg.get("models", {}).get("vlm", "llava:7b")
                                _llm = OllamaClient(api_url=_ollama_url)
                                _b64 = encode_image_b64(local_path)
                                _ans = _llm.generate(
                                    model=_vlm_model,
                                    prompt="\u8acb\u63cf\u8ff0\u9019\u5f35\u5716\u7247\u7684\u5167\u5bb9\uff0c\u7528\u7e41\u9ad4\u4e2d\u6587\u56de\u7b54\u3002",
                                    images=[_b64],
                                )
                                send_message(
                                    f"\U0001f916 VLM \u5206\u6790\u7d50\u679c\uff1a\n\n{_ans}", _cid
                                )
                            except Exception as _exc:
                                send_message(
                                    f"\u274c \u7167\u7247\u5206\u6790\u5931\u6557: {_exc}", _cid
                                )

                        threading.Thread(target=_handle_photo, daemon=True).start()
                        continue
                    # ── End multimodal routing ─────────────────────────────────────

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
                            ["pkill", "-15", "-f", "doc_parser/scripts/run_all.py"], check=False
                        )
                        subprocess.run(
                            ["pkill", "-15", "-f", "audio_transcriber/scripts/run_all.py"],
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
                                f"✅ 模型已切換為 `{arg}`，下次任務生效。",
                                chat_id,
                            )
                        else:
                            prefs = _load_user_prefs()
                            current = prefs.get(
                                "active_model",
                                "(未設定，使用各 Skill 預設模型)",
                            )
                            send_message(f"🤖 目前模型: `{current}`", chat_id)

                    elif text.startswith("/reveal "):
                        card_id = text[8:].strip()
                        from core.services.sm2 import SM2Engine

                        engine = SM2Engine(_workspace_root)
                        card = engine.db["cards"].get(card_id)
                        if not card:
                            send_message("❌ 找不到此卡片或已過期。", chat_id)
                        else:
                            msg = f"🎴 **Answer**:\n\n{card['back']}\n\n請回覆 `/rate {card_id} <0-5>` 評分 (5=完美, 0=忘記)"
                            send_message(msg, chat_id)

                    elif text.startswith("/rate "):
                        parts = text.split()
                        if len(parts) >= 3:
                            card_id = parts[1]
                            try:
                                quality = int(parts[2])
                                from core.services.sm2 import SM2Engine

                                engine = SM2Engine(_workspace_root)
                                engine.review_card(card_id, quality)
                                next_date = engine.db["cards"][card_id]["next_review"]
                                send_message(f"✅ 評分已記錄！下次複習: {next_date}", chat_id)
                            except ValueError:
                                send_message("⚠️ 評分必須是 0-5 的數字。", chat_id)
                        else:
                            send_message("用法: `/rate <card_id> <0-5>`", chat_id)

                    elif text.startswith("/hitl "):
                        # H2 + P0-5: HITL callback — searches ALL skill pending dirs
                        parts = text.split()
                        if len(parts) >= 3:
                            resolution = parts[1].lower()
                            trace_id = parts[2]

                            # P0-5: HITLManager stores events under data/<skill>/state/hitl_pending/
                            # We must search across all skills, not just _workspace_root
                            snapshot = None
                            searched_dirs = []
                            data_root = os.path.join(_workspace_root, "data")
                            if os.path.isdir(data_root):
                                for skill_dir in os.listdir(data_root):
                                    skill_base = os.path.join(data_root, skill_dir)
                                    if not os.path.isdir(skill_base):
                                        continue
                                    hitl_mgr = HITLManager(base_dir=skill_base)
                                    searched_dirs.append(skill_dir)
                                    result = hitl_mgr.resolve(trace_id, resolution)
                                    if result is not None:
                                        snapshot = result
                                        break

                            if snapshot is not None:
                                send_message(
                                    f"\u2705 HITL \u5df2\u8655\u7406: `{trace_id}`\n\u6c7a\u5b9a: {resolution}\n\u7ba1\u7dda\u5c07\u81ea\u52d5\u6062\u5fa9\u3002",
                                    chat_id,
                                )
                            else:
                                send_message(
                                    f"\u26a0\ufe0f \u627e\u4e0d\u5230 HITL \u4e8b\u4ef6 `{trace_id}` "
                                    f"(\u641c\u5c0b\u4e86 {len(searched_dirs)} \u500b Skill)\u3002\u53ef\u80fd\u5df2\u8655\u7406\u6216 ID \u932f\u8aa4\u3002",
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
                            "/hitl approve|skip <trace_id> - \u56de\u61c9\u7cfb\u7d71\u66ab\u505c\u7684\u4ecb\u5165\u4e8b\u4ef6\n\n"
                            "[\u6392\u7a0b\u4ee3\u7406 P2]\n"
                            "/schedule list - \u67e5\u770b\u6240\u6709\u6392\u7a0b\u4efb\u52d9\n"
                            "/schedule add <id> <cron> <skill> <\u8aaa\u660e> - \u65b0\u589e\u6392\u7a0b\n"
                            "/schedule remove <id> - \u522a\u9664\u6392\u7a0b\n"
                            '  \u4f8b: /schedule add rss_daily "0 7 * * *" academic_edu_assistant \u6bcf\u65e5\u6293\u53d6',
                            chat_id,
                        )

                    # ── P2-3: /schedule commands ───────────────────────────────────
                    elif text.startswith("/schedule"):
                        from core.orchestration.scheduler import get_scheduler

                        sched = get_scheduler(_workspace_root)
                        args = text.split(None, 4)  # /schedule <sub> [id] [cron] [skill] [desc]
                        sub = args[1].lower() if len(args) > 1 else "list"

                        if sub == "list":
                            send_message(sched.format_status(), chat_id)

                        elif sub == "add" and len(args) >= 5:
                            # /schedule add <id> <"cron expr"> <skill> [desc]
                            job_id = args[2]
                            # Support cron in quotes or bare (5 fields)
                            rest = args[3] if len(args) > 3 else ""
                            # Try to extract 5-field cron from start of rest
                            rest_parts = rest.split()
                            if len(rest_parts) >= 5:
                                cron_expr = " ".join(rest_parts[:5])
                                skill_name = (
                                    rest_parts[5]
                                    if len(rest_parts) > 5
                                    else "academic_edu_assistant"
                                )
                                description = (
                                    " ".join(rest_parts[6:]) if len(rest_parts) > 6 else ""
                                )
                            else:
                                send_message(
                                    "\u26a0\ufe0f \u683c\u5f0f: /schedule add <id> <\u5206 \u6642 \u65e5 \u6708 \u9031> <skill> [\u8aaa\u660e]",
                                    chat_id,
                                )
                                continue  # type: ignore[misc]
                            skill_dir = os.path.join(_workspace_root, "skills", skill_name)
                            run_all = os.path.join(skill_dir, "scripts", "run_all.py")
                            command = [sys.executable, run_all, "--process-all"]
                            ok = sched.add_job(
                                job_id=job_id,
                                cron_expr=cron_expr,
                                skill_name=skill_name,
                                command=command,
                                description=description,
                            )
                            if ok:
                                send_message(
                                    f"\u2705 \u6392\u7a0b\u5df2\u65b0\u589e: `{job_id}` ({cron_expr})",
                                    chat_id,
                                )
                            else:
                                send_message(
                                    f"\u26a0\ufe0f job_id `{job_id}` \u5df2\u5b58\u5728\u3002",
                                    chat_id,
                                )

                        elif sub == "remove" and len(args) >= 3:
                            job_id = args[2]
                            ok = sched.remove_job(job_id)
                            msg = (
                                f"\u2705 \u6392\u7a0b\u5df2\u522a\u9664: `{job_id}`"
                                if ok
                                else f"\u26a0\ufe0f \u627e\u4e0d\u5230\u6392\u7a0b: `{job_id}`"
                            )
                            send_message(msg, chat_id)

                        else:
                            send_message(
                                "\u7528\u6cd5:\n"
                                "/schedule list\n"
                                "/schedule add <id> <\u5206 \u6642 \u65e5 \u6708 \u9031> <skill> [\u8aaa\u660e]\n"
                                "/schedule remove <id>",
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
