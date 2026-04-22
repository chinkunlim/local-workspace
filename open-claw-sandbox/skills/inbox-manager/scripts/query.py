"""
skills/inbox-manager/scripts/query.py
======================================
CLI tool for Open Claw to list, add, or remove PDF routing rules
in core/inbox_config.json. Designed to be invoked by Open Claw's
intent-routing when the user asks about routing settings.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

# ── Path bootstrap ─────────────────────────────────────────────────────────────
_script_dir = os.path.dirname(os.path.abspath(__file__))
_workspace_root = os.path.abspath(os.path.join(_script_dir, "..", "..", ".."))
_config_path = os.path.join(_workspace_root, "core", "inbox_config.json")


def _load() -> dict:
    if not os.path.exists(_config_path):
        print(f"❌ 找不到設定檔: {_config_path}")
        sys.exit(1)
    with open(_config_path, encoding="utf-8") as f:
        return json.load(f)


def _save(cfg: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(_config_path), suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, _config_path)


# ── Commands ───────────────────────────────────────────────────────────────────


def cmd_list(cfg: dict) -> None:
    """Print a human-friendly summary of all routing rules."""
    rules: list[dict] = cfg.get("pdf_routing_rules", [])

    # Group by routing mode
    groups: dict[str, list[dict]] = {"audio_ref": [], "both": [], "doc_parser": []}
    for r in rules:
        mode = r.get("routing", "audio_ref")
        groups.setdefault(mode, []).append(r)

    mode_labels = {
        "audio_ref": "🔍 audio_ref  (語音校對參考)",
        "both": "📦 both       (同時解析 + 語音校對)",
        "doc_parser": "📄 doc_parser (獨立 Markdown 解析)",
    }

    print("\n📬 Open Claw Inbox — PDF 路由規則一覽")
    print("=" * 55)
    for mode, label in mode_labels.items():
        entries = groups.get(mode, [])
        if not entries:
            continue
        print(f"\n{label}")
        print("-" * 55)
        for entry in entries:
            pat = entry.get("pattern", "")
            desc = entry.get("description", "")
            print(f"  {pat:<20} → {desc}")

    print("\n" + "=" * 55)
    print(f"共 {len(rules)} 條規則 | 設定檔: core/inbox_config.json")
    print(
        "\n提示：後綴以 _ 開頭者為「結尾比對」，其餘為「任意位置比對」\n"
        "路由模式說明:\n"
        "  audio_ref  → 送往 audio-transcriber 詞庫供語音校對\n"
        "  doc_parser → 送往 doc-parser 轉為 Markdown 筆記\n"
        "  both       → 同時執行以上兩者（複製一份）\n"
    )


def cmd_add(cfg: dict, pattern: str, routing: str, description: str) -> None:
    rules: list[dict] = cfg.setdefault("pdf_routing_rules", [])
    # Check for duplicates
    for r in rules:
        if r.get("pattern", "").lower() == pattern.lower():
            print(
                f"⚠️  規則 '{pattern}' 已存在 (routing={r['routing']})，使用 --remove 先刪除再新增。"
            )
            return
    rules.append({"pattern": pattern, "routing": routing, "description": description})
    _save(cfg)
    print(f"✅ 已新增規則: '{pattern}' → {routing}  ({description})")


def cmd_remove(cfg: dict, pattern: str) -> None:
    rules: list[dict] = cfg.get("pdf_routing_rules", [])
    before = len(rules)
    cfg["pdf_routing_rules"] = [r for r in rules if r.get("pattern", "").lower() != pattern.lower()]
    after = len(cfg["pdf_routing_rules"])
    if before == after:
        print(f"⚠️  找不到規則 '{pattern}'，無任何變更。")
    else:
        _save(cfg)
        print(f"✅ 已刪除規則: '{pattern}'")


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Inbox Manager — 管理 Open Claw 收件匣路由規則")
    sub = parser.add_subparsers(dest="cmd")

    # list (default)
    sub.add_parser("list", help="列出所有路由規則")

    # add
    p_add = sub.add_parser("add", help="新增路由規則")
    p_add.add_argument("pattern", help="後綴或關鍵字 (e.g. _ppt or 課件)")
    p_add.add_argument(
        "--routing",
        choices=["audio_ref", "both", "doc_parser"],
        default="audio_ref",
        help="路由模式 (預設: audio_ref)",
    )
    p_add.add_argument("--description", default="", help="說明文字")

    # remove
    p_rm = sub.add_parser("remove", help="刪除路由規則")
    p_rm.add_argument("pattern", help="要刪除的後綴或關鍵字")

    # Also support legacy flags for Open Claw direct invocation
    parser.add_argument("--list", action="store_true", help="列出所有規則")
    parser.add_argument("--add", metavar="PATTERN", help="新增規則")
    parser.add_argument(
        "--routing", choices=["audio_ref", "both", "doc_parser"], default="audio_ref"
    )
    parser.add_argument("--description", default="")
    parser.add_argument("--remove", metavar="PATTERN", help="刪除規則")

    args = parser.parse_args()
    cfg = _load()

    # Sub-command mode
    if args.cmd == "list" or (not args.cmd and args.list):
        cmd_list(cfg)
    elif args.cmd == "add":
        cmd_add(cfg, args.pattern, args.routing, args.description)
    elif args.cmd == "remove":
        cmd_remove(cfg, args.pattern)
    # Legacy --flag mode
    elif args.add:
        cmd_add(cfg, args.add, args.routing, args.description)
    elif args.remove:
        cmd_remove(cfg, args.remove)
    else:
        # Default: just list
        cmd_list(cfg)


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
