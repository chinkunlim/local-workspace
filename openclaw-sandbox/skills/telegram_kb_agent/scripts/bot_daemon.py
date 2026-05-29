import os
import subprocess
import sys
import threading
import time

import requests

from core.services.hitl_manager import HITLManager
from core.services.telegram_bot import _get_bot_config, send_inline_keyboard, send_message
from core.utils.atomic_writer import AtomicWriter
from core.utils.log_manager import build_logger
from core.utils.workspace import get_workspace_root

_workspace_root = get_workspace_root()

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
    status_script = os.path.join(_workspace_root, "core", "cli", "check_status.py")
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
    _user_states = {}

    while True:
        try:
            resp = requests.get(url, params={"offset": offset, "timeout": 30}, timeout=40)
            if resp.ok:
                data = resp.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    callback_query = update.get("callback_query")
                    if callback_query:
                        msg = callback_query.get("message", {})
                        chat_id = str(msg.get("chat", {}).get("id", ""))
                        text = callback_query.get("data", "").strip()
                        query_id = callback_query.get("id")
                        # 停止載入轉圈圈
                        requests.post(
                            f"https://api.telegram.org/bot{token}/answerCallbackQuery",
                            json={"callback_query_id": query_id},
                        )
                    else:
                        msg = update.get("message", {})
                        chat_id = str(msg.get("chat", {}).get("id", ""))
                        text = msg.get("text", "").strip()

                    from core.services.security_manager import SecurityManager

                    text = SecurityManager.sanitize_user_input(text)

                    # Security check
                    if chat_id not in allowed_users:
                        continue

                    # ── Handle State: WAITING_ARGS ─────────────────────────────────
                    if text == "/cancel":
                        if chat_id in _user_states:
                            del _user_states[chat_id]
                            send_message("✅ 已取消當前操作。", chat_id)
                        else:
                            send_message("沒有正在進行的操作。", chat_id)
                        continue

                    if (
                        chat_id in _user_states
                        and _user_states[chat_id].get("step") == "WAITING_ARGS"
                    ):
                        stage_name = _user_states[chat_id]["stage"]
                        del _user_states[chat_id]

                        args = []
                        if text.lower() not in ["none", "skip", ""]:
                            import shlex

                            try:
                                args = shlex.split(text)
                            except Exception:
                                args = text.split()

                        send_message(f"⚙️ 正在背景啟動 {stage_name}...", chat_id)
                        run_script = os.path.join(
                            _workspace_root, "skills", stage_name, "scripts", "run_all.py"
                        )
                        cmd = ["uv", "run", run_script, *args]
                        subprocess.Popen(cmd)
                        send_message(
                            f"✅ {stage_name} 已加入執行列。參數: {' '.join(args) if args else '無'}",
                            chat_id,
                        )
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
                                    prompt="請描述這張圖片的內容，用繁體中文回答。",
                                    images=[_b64],
                                )
                                _llm.unload_model(_vlm_model)
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

                    elif text.startswith("/run_stage"):
                        parts = text.split(maxsplit=1)
                        if len(parts) == 1:
                            # List available stages
                            skills_dir = os.path.join(_workspace_root, "skills")
                            stages = []
                            if os.path.isdir(skills_dir):
                                for d in os.listdir(skills_dir):
                                    if os.path.isfile(
                                        os.path.join(skills_dir, d, "scripts", "run_all.py")
                                    ):
                                        stages.append(d)
                            if stages:
                                msg = (
                                    "請使用 `/run_stage <stage_name>`。目前可用的階段有：\n- "
                                    + "\n- ".join(stages)
                                )
                            else:
                                msg = "找不到任何可用的管線階段。"
                            send_message(msg, chat_id)
                        else:
                            stage_name = parts[1].strip()
                            script_path = os.path.join(
                                _workspace_root, "skills", stage_name, "scripts", "run_all.py"
                            )
                            if not os.path.isfile(script_path):
                                send_message(f"❌ 找不到階段 {stage_name} 的執行腳本。", chat_id)
                            else:
                                _user_states[chat_id] = {
                                    "step": "WAITING_ARGS",
                                    "stage": stage_name,
                                }
                                send_message(
                                    f"👉 準備啟動 {stage_name}。\n請輸入要附加的 CLI 參數（例如 `--skip`）。\n如果不需要附加參數，請回覆 `none` 或 `skip`。\n輸入 `/cancel` 可取消。",
                                    chat_id,
                                )

                    elif text == "/run" or text == "/resume":
                        send_message("⚙️ 正在啟動管線處理任務 (將在終端機中顯示)...", chat_id)
                        run_script = os.path.join(
                            _workspace_root, "core", "orchestration", "run_all_pipelines.py"
                        )
                        import platform

                        if platform.system() == "Darwin":
                            # Open in a new Terminal window on Mac, or reuse an existing one named OpenClaw
                            apple_script = f"""
                            tell application "Terminal"
                                activate
                                set targetWindow to missing value
                                repeat with w in windows
                                    if name of w contains "OpenClaw" then
                                        set targetWindow to w
                                        exit repeat
                                    end if
                                end repeat

                                if targetWindow is missing value then
                                    set newTab to do script "cd '{_workspace_root}' && uv run '{run_script}'"
                                    set custom title of newTab to "OpenClaw"
                                else
                                    do script "cd '{_workspace_root}' && uv run '{run_script}'" in targetWindow
                                end if
                            end tell
                            """
                            subprocess.Popen(["osascript", "-e", apple_script])
                        else:
                            subprocess.Popen([sys.executable, run_script])
                        send_message(
                            "✅ 任務已在終端機彈出執行，使用 /status 可隨時查詢進度。", chat_id
                        )

                    elif text == "/pause":
                        send_message("⏸️ 正在暫停管線並釋放記憶體...", chat_id)
                        # 發送 SIGTERM (15) 給所有相關行程，觸發優雅暫停與斷點存檔
                        subprocess.run(
                            ["pkill", "-15", "-f", "core/orchestration/run_all_pipelines.py"],
                            check=False,
                        )
                        subprocess.run(["pkill", "-15", "-f", "scripts/run_all.py"], check=False)
                        send_message(
                            "✅ 系統已發送暫停訊號！任務將在建立斷點後結束，記憶體隨即釋放。",
                            chat_id,
                        )

                    elif text in ["/start_system", "/wakeup"]:
                        send_message(
                            "🚀 正在啟動 Open Claw 核心生態系 (包含 start.sh 與 inbox_daemon)...",
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

                            if resolution in ["idea_approve", "idea_skip"]:
                                filepath = trace_id
                                if resolution == "idea_approve":
                                    if os.path.exists(filepath):
                                        filename = os.path.basename(filepath)
                                        inbox_path = os.path.join(
                                            _workspace_root, "data", "raw", "inbox", filename
                                        )
                                        os.makedirs(os.path.dirname(inbox_path), exist_ok=True)
                                        os.rename(filepath, inbox_path)
                                        send_message(
                                            "✅ 已將靈感投入收件匣，即刻啟動深度研究！", chat_id
                                        )
                                    else:
                                        send_message(
                                            "❌ 找不到該靈感檔案，可能已啟動或刪除。", chat_id
                                        )
                                else:
                                    send_message("⏸️ 好的，靈感保留在暫存區。", chat_id)
                                continue

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
                            "👋 歡迎使用 Open Claw 全能遙控中樞！\n\n"
                            "[進度管理]\n"
                            "/status - 查看系統處理佇列進度\n"
                            "/run 或 /resume - 依序執行待辦任務\n"
                            "/pause - 暫停執行並釋放所有記憶體\n\n"
                            "[系統管理]\n"
                            "/wakeup 或 /start_system - 開啟整個生態系專案 (含 inbox_daemon)\n"
                            "/stop_system - 關閉整個生態系專案 (不含 Bot)\n\n"
                            "[知識問答]\n"
                            "/query <問題> - 在知識庫中發問\n\n"
                            "[靈感捕捉]\n"
                            "/idea <內容> #<標籤> - 記錄靈感，週末自動提醒啟動研究\n\n"
                            "[模型管理]\n"
                            "/model <名稱> - 切換 LLM 模型 (空白 = 查詢目前)\n\n"
                            "[HITL 介入]\n"
                            "/hitl approve|skip <trace_id> - 回應系統暫停的介入事件\n\n"
                            "[排程代理 P2]\n"
                            "/schedule list - 查看所有排程任務\n"
                            "/schedule add <id> <cron> <skill> <說明> - 新增排程\n"
                            "/schedule remove <id> - 刪除排程\n"
                            '  例: /schedule add rss_daily "0 7 * * *" academic_edu_assistant 每日抓取',
                            chat_id,
                        )

                    elif text.startswith("/idea "):
                        idea_content = text[6:].strip()
                        if not idea_content:
                            send_message("⚠️ 用法: `/idea [您的點子內容] #[標籤]`", chat_id)
                            continue

                        import uuid

                        idea_id = str(uuid.uuid4())[:8]
                        filename = f"Ollama_Idea_{idea_id}.md"

                        drafts_dir = os.path.join(_workspace_root, "data", "raw", "ideas_drafts")
                        os.makedirs(drafts_dir, exist_ok=True)
                        filepath = os.path.join(drafts_dir, filename)

                        AtomicWriter.write_text(filepath, idea_content)

                        # Add a cron job to remind on Saturday at 10:00 (for weekend)
                        from core.orchestration.scheduler import get_scheduler

                        sched = get_scheduler(_workspace_root)
                        cron_expr = "0 10 * * 6"

                        script_path = os.path.join(
                            _workspace_root, "core", "scripts", "idea_reminder.py"
                        )
                        command = [sys.executable, script_path, filepath]
                        job_id = f"idea_remind_{idea_id}"

                        sched.add_job(
                            job_id=job_id,
                            cron_expr=cron_expr,
                            skill_name="telegram_kb_agent",
                            command=command,
                            description=f"靈感提醒: {filename}",
                            enabled=True,
                        )
                        send_message(
                            f"✅ 您的靈感已暫存！\n我已將它排入週末 (星期六早上 10:00) 的提醒排程。\n(`{filename}`)",
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
