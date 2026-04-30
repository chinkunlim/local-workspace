"""
SecurityManager — OpenClaw Shared Security Framework
=====================================================
Playwright 操作授權邊界管理器。

設計原則（CLAUDE_v2.1.md D010/D011）：
- 所有 page.goto() 前必須呼叫 validate_navigation(url)
- URL 不在 security_policy.yaml 白名單中 → SecurityViolationError + 審計日誌 + 中止
- 系統不儲存、不讀取、不傳輸任何 Google 帳號憑證
- 多帳號防呆：Profile 路徑名稱比對（不存取 accounts.google.com）
- 所有 Playwright 動作記錄到 security_audit.log

Usage:
    from core.services.security_manager import SecurityManager, SecurityViolationError

    sm = SecurityManager(config_dir="skills/doc-parser/config")
    sm.validate_navigation("https://gemini.google.com/app")   # OK
    sm.validate_navigation("https://mail.google.com/")         # → SecurityViolationError
"""

from datetime import datetime
import fnmatch
import os
import re
from typing import Optional

import yaml


class SecurityViolationError(Exception):
    """Raised when a Playwright action violates the security policy."""

    pass


class SecurityManager:
    """
    Playwright 操作授權邊界控制器。

    Args:
        config_dir: 包含 security_policy.yaml 的資料夾路徑。
        audit_log_path: security_audit.log 的路徑。若 None，預設為 config_dir/../logs/security_audit.log。
    """

    def __init__(self, config_dir: str, audit_log_path: Optional[str] = None):
        self.config_dir = config_dir
        self.policy = self._load_policy()

        if audit_log_path is None:
            skill_root = os.path.dirname(config_dir)
            audit_log_path = os.path.join(
                os.environ.get("WORKSPACE_DIR", os.path.abspath(os.path.join(skill_root, ".."))),
                "data",
                "doc-parser",
                "logs",
                "security_audit.log",
            )
        self.audit_log_path = audit_log_path
        os.makedirs(os.path.dirname(audit_log_path), exist_ok=True)

    # ------------------------------------------------------------------ #
    #  Policy Loading                                                      #
    # ------------------------------------------------------------------ #

    def _load_policy(self) -> dict:
        policy_path = os.path.join(self.config_dir, "security_policy.yaml")
        if not os.path.exists(policy_path):
            raise FileNotFoundError(
                f"security_policy.yaml not found at {policy_path}. "
                "This file is required and must ONLY be modified by the user."
            )
        with open(policy_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    # ------------------------------------------------------------------ #
    #  Validation                                                          #
    # ------------------------------------------------------------------ #

    def validate_navigation(self, url: str) -> bool:
        """
        Validate a URL before Playwright navigates to it.

        Returns True if allowed. Raises SecurityViolationError if forbidden.
        Raises SecurityViolationError if not in allowed list.
        """
        url_lower = url.lower().rstrip("/")

        # 1. Check forbidden list first (higher priority)
        forbidden = self.policy.get("forbidden_actions", {}).get("navigate", [])
        for pattern in forbidden:
            if self._url_matches(url_lower, pattern):
                self._audit("NAVIGATE", "BLOCKED", url)
                raise SecurityViolationError(
                    f"🚫 [Security] Navigation to '{url}' BLOCKED by security_policy.yaml.\n"
                    f"   Matched forbidden pattern: '{pattern}'\n"
                    f"   Edit security_policy.yaml to change this policy (user only)."
                )

        # 2. Check allowed list
        allowed = self.policy.get("allowed_actions", {}).get("navigate", [])
        for pattern in allowed:
            if self._url_matches(url_lower, pattern):
                self._audit("NAVIGATE", "ALLOWED", url)
                return True

        # 3. Not in any list → deny by default
        self._audit("NAVIGATE", "BLOCKED", url)
        raise SecurityViolationError(
            f"🚫 [Security] Navigation to '{url}' BLOCKED — not in allowed list.\n"
            f"   Add to allowed_actions.navigate in security_policy.yaml to permit (user only)."
        )

    def validate_action(self, action_type: str, target: str) -> bool:
        """
        Validate a non-navigation Playwright action (click, fill, download, etc.).

        Returns True if allowed. Raises SecurityViolationError if forbidden.
        """
        action_upper = action_type.upper()

        forbidden_actions = self.policy.get("forbidden_actions", {}).get("actions", [])
        for pattern in forbidden_actions:
            if fnmatch.fnmatch(target.lower(), pattern.lower()):
                self._audit(action_upper, "BLOCKED", target)
                raise SecurityViolationError(
                    f"🚫 [Security] Action '{action_type}' on '{target}' BLOCKED by policy."
                )

        self._audit(action_upper, "ALLOWED", target)
        return True

    def validate_download(self, file_path: str) -> bool:
        """
        Validate a file download path and extension.
        """
        download_policy = self.policy.get("allowed_actions", {}).get("download", {})
        allowed_path = os.path.expanduser(download_policy.get("path", "~/Downloads/"))
        allowed_types = download_policy.get("file_types", [".md", ".json"])

        abs_path = os.path.abspath(os.path.expanduser(file_path))
        abs_allowed = os.path.abspath(allowed_path)

        ext = os.path.splitext(file_path)[1].lower()

        if not abs_path.startswith(abs_allowed):
            self._audit("DOWNLOAD", "BLOCKED", file_path)
            raise SecurityViolationError(
                f"🚫 [Security] Download to '{file_path}' BLOCKED — outside allowed path '{allowed_path}'."
            )

        if ext not in allowed_types:
            self._audit("DOWNLOAD", "BLOCKED", file_path)
            raise SecurityViolationError(
                f"🚫 [Security] Download of '{ext}' file BLOCKED — only {allowed_types} allowed."
            )

        self._audit("DOWNLOAD", "ALLOWED", file_path)
        return True

    def verify_account_intent(self, chrome_profile: str, account_hint: str) -> bool:
        """
        Profile 路徑比對防呆。顯示提示讓使用者肉眼確認，不存取 accounts.google.com。

        Returns True if user confirms, False otherwise.
        """
        profile_name = os.path.basename(os.path.normpath(chrome_profile))
        print(f'\n🔐 Chrome Profile: {profile_name} — 備忘: "{account_hint}"')
        try:
            answer = input("這是你想要使用的帳號嗎？[是/否] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return answer in ("是", "y", "yes", "1")

    # ------------------------------------------------------------------ #
    #  Audit Logging                                                       #
    # ------------------------------------------------------------------ #

    def _audit(self, action: str, result: str, target: str):
        """Write to security_audit.log."""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        line = f"[{timestamp}] [{action:<10}] [{result:<7}] → {target}\n"
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass  # Audit failure must not block pipeline

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _url_matches(url: str, pattern: str) -> bool:
        """
        Match URL against a glob-like pattern.
        e.g. "gemini.google.com/*" matches "https://gemini.google.com/app"
        """
        # Normalize: strip scheme
        clean_url = re.sub(r"^https?://", "", url)
        clean_pattern = re.sub(r"^https?://", "", pattern)
        return fnmatch.fnmatch(clean_url, clean_pattern)
