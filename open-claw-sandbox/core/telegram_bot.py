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
        print(f"⚠️ [TelegramBot] 無法讀取 openclaw.json: {e}")
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
                print(f"⚠️ [TelegramBot] 推播失敗給 {user_id}: {resp.text}")
        except Exception as e:
            print(f"⚠️ [TelegramBot] 推播連線錯誤: {e}")
            success = False

    return success
