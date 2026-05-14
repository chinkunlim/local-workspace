"""
core/telegram_bot.py — Lightweight Telegram Bot Integration
=========================================================
提供簡單的 Telegram 推播功能給 TaskQueue，
並且讀取 ~/.openclaw/openclaw.json 中的全局 Telegram 設定。
"""

import json
import os
from typing import List, Tuple

import requests

from core.utils.log_manager import build_logger

logger = build_logger(__name__, console=True)


def _get_bot_config() -> Tuple[str, List[str]]:
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    if not os.path.exists(config_path):
        return "", []

    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
            telegram_cfg = cfg.get("channels", {}).get("telegram", {})
            token = telegram_cfg.get("botToken", "")
            users = telegram_cfg.get("allowFrom", [])
            return token, users
    except Exception as e:
        logger.info(f"⚠️ [TelegramBot] 無法讀取 openclaw.json: {e}")
        return "", []


def send_message(text: str, chat_id: str = None) -> bool:
    """Send a message to allowed_users (or specific chat_id)."""
    token, allowed_users = _get_bot_config()
    if not token:
        # 如果使用者尚未設定 token，靜默返回，不報錯以免干擾主要流程
        return False

    targets = [chat_id] if chat_id else allowed_users
    if not targets:
        return False

    success = True
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    for user_id in targets:
        try:
            resp = requests.post(url, json={"chat_id": user_id, "text": text}, timeout=10)
            if not resp.ok:
                success = False
                logger.info(f"⚠️ [TelegramBot] 推播失敗給 {user_id}: {resp.text}")
        except Exception as e:
            logger.info(f"⚠️ [TelegramBot] 推播連線錯誤: {e}")
            success = False

    return success


def send_inline_keyboard(
    text: str,
    buttons: list,
    chat_id: str = None,
) -> bool:
    """Send a message with an inline keyboard (for HITL interventions).

    H1: Enables interactive HITL buttons without requiring python-telegram-bot.

    Args:
        text:    The message text (supports Markdown).
        buttons: List of rows; each row is a list of (label, callback_data) tuples.
                 Example: [[("Approve", "hitl:abc:approve"), ("Skip", "hitl:abc:skip")]]
        chat_id: Optional specific chat ID. Defaults to all allowed users.

    Returns:
        True if all messages were sent successfully.
    """
    token, allowed_users = _get_bot_config()
    if not token:
        return False

    targets = [chat_id] if chat_id else allowed_users
    if not targets:
        return False

    inline_keyboard = [
        [{"text": label, "callback_data": data} for label, data in row] for row in buttons
    ]
    reply_markup = {"inline_keyboard": inline_keyboard}

    success = True
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for user_id in targets:
        try:
            resp = requests.post(
                url,
                json={
                    "chat_id": user_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "reply_markup": reply_markup,
                },
                timeout=10,
            )
            if not resp.ok:
                success = False
        except Exception as e:
            logger.info(
                f"\u26a0\ufe0f [TelegramBot] send_inline_keyboard \u9023\u7dda\u932f\u8aa4: {e}"
            )
            success = False
    return success


def send_hitl_prompt(
    trace_id: str,
    phase: str,
    reason: str,
    chat_id: str = None,
) -> bool:
    """Convenience wrapper: send a pre-formatted HITL intervention message with Approve/Skip buttons.

    Args:
        trace_id: The HITLEvent trace ID (used as callback_data).
        phase:    The pipeline phase that triggered the intervention.
        reason:   Human-readable explanation of why the pipeline paused.
        chat_id:  Optional specific chat ID.
    """
    text = (
        f"\u26a0\ufe0f *OpenClaw HITL \u4ecb\u5165*\n"
        f"Phase: `{phase}`\n"
        f"\u539f\u56e0: {reason}\n"
        f"Trace ID: `{trace_id}`\n\n"
        f"\u8acb\u9078\u64c7\u8655\u7406\u65b9\u5f0f\uff1a"
    )
    buttons = [
        [
            ("\u2705 Approve", f"/hitl approve {trace_id}"),
            ("\u23ed\ufe0f Skip", f"/hitl skip {trace_id}"),
        ]
    ]
    return send_inline_keyboard(text, buttons, chat_id=chat_id)


# ---------------------------------------------------------------------------
# P1-4: Multimodal File Download Helpers
# ---------------------------------------------------------------------------


def download_file(file_id: str, dest_dir: str) -> str:
    """Download a Telegram file to dest_dir and return the local absolute path.

    Uses the Telegram Bot API getFile endpoint to resolve the file_path,
    then downloads the binary content. Raises RuntimeError on failure.

    Args:
        file_id:  Telegram file_id from a message object (voice/audio/photo/document).
        dest_dir: Local directory where the file will be saved.

    Returns:
        Absolute path to the downloaded file.

    Raises:
        RuntimeError: If the bot token is missing or the API call fails.
    """
    token, _ = _get_bot_config()
    if not token:
        raise RuntimeError("[TelegramBot] download_file: bot token not configured.")

    # Step 1: Resolve file_path from file_id
    meta_resp = requests.get(
        f"https://api.telegram.org/bot{token}/getFile",
        params={"file_id": file_id},
        timeout=15,
    )
    if not meta_resp.ok:
        raise RuntimeError(f"[TelegramBot] getFile failed for file_id={file_id}: {meta_resp.text}")
    file_path_remote = meta_resp.json()["result"]["file_path"]

    # Step 2: Download the binary content
    download_url = f"https://api.telegram.org/file/bot{token}/{file_path_remote}"
    bin_resp = requests.get(download_url, timeout=120, stream=True)
    if not bin_resp.ok:
        raise RuntimeError(
            f"[TelegramBot] File download failed for {file_path_remote}: {bin_resp.status_code}"
        )

    os.makedirs(dest_dir, exist_ok=True)
    local_filename = os.path.basename(file_path_remote)
    local_path = os.path.join(dest_dir, local_filename)

    with open(local_path, "wb") as f:
        for chunk in bin_resp.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)

    return os.path.abspath(local_path)


def download_voice(message: dict, dest_dir: str) -> str:
    """Convenience wrapper: extract file_id from a Telegram voice/audio message dict.

    Accepts a `message` dict from the Telegram getUpdates response and downloads
    the attachment to dest_dir. Prefers `voice` > `audio` > `document`.

    Args:
        message:  The `message` sub-dict from a Telegram update.
        dest_dir: Local directory to save the file.

    Returns:
        Absolute local path to the downloaded file.

    Raises:
        ValueError:   If no downloadable attachment is found in the message.
        RuntimeError: If the download fails.
    """
    for key in ("voice", "audio", "document"):
        attachment = message.get(key)
        if attachment:
            file_id = attachment.get("file_id", "")
            if file_id:
                return download_file(file_id, dest_dir)
    raise ValueError("[TelegramBot] download_voice: no voice/audio/document found in message.")
