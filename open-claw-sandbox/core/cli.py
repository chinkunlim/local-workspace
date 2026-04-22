"""Shared CLI helpers for skill entrypoints."""

from __future__ import annotations

import argparse


def build_skill_parser(
    description: str,
    *,
    include_subject: bool = False,
    include_force: bool = False,
    include_resume: bool = False,
    include_interactive: bool = False,
    include_start_phase: bool = False,
    include_process_all: bool = False,
    include_config: bool = False,
    include_log_json: bool = False,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    if include_interactive:
        parser.add_argument("--interactive", "-i", action="store_true", help="啟用互動式分段確認")
    if include_force:
        parser.add_argument("--force", "-f", action="store_true", help="強制重新處理所有項目")
    if include_resume:
        parser.add_argument("--resume", "-r", action="store_true", help="強制從 checkpoint 繼續")
    if include_subject:
        parser.add_argument("--subject", "-s", type=str, help="只處理指定 subject")
        parser.add_argument(
            "--file", type=str, help="從指定檔案名稱開始 (或配合 --single 只處理該檔案)"
        )
        parser.add_argument(
            "--single",
            action="store_true",
            help="啟用單檔處理模式 (僅處理 --file 指定的檔案，不接續處理後續檔案)",
        )
    if include_start_phase:
        parser.add_argument(
            "--from",
            dest="start_phase",
            type=int,
            default=1,
            choices=range(1, 100),
            help="從指定 phase 開始",
        )
    if include_process_all:
        parser.add_argument(
            "--process-all",
            action="store_true",
            help="非互動模式：處理所有待辦項目 (適合排程/Telegram)",
        )
    if include_config:
        parser.add_argument("--config", type=str, help="指定自訂的 config.yaml 路徑")
    if include_log_json:
        parser.add_argument(
            "--log-json", action="store_true", help="啟用 JSON 格式的結構化日誌輸出"
        )
    return parser
