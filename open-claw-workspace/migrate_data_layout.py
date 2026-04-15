# -*- coding: utf-8 -*-
"""Migrate legacy skill data folders to the canonical input/output/state/logs layout."""

from __future__ import annotations

import argparse
import os
import sys

WORKSPACE_DIR = os.path.abspath(os.path.dirname(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from core import DataLayoutManager


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate OpenClaw skill data layout")
    parser.add_argument("--skill", action="append", choices=["voice-memo", "pdf-knowledge"], help="Skill to migrate")
    parser.add_argument("--dry-run", action="store_true", help="Show planned actions without changing files")
    parser.add_argument("--all", action="store_true", help="Migrate both built-in skills")
    args = parser.parse_args()

    skills = args.skill or []
    if args.all or not skills:
        skills = ["voice-memo", "pdf-knowledge"]

    for skill_name in skills:
        plan = DataLayoutManager.migrate(WORKSPACE_DIR, skill_name, dry_run=args.dry_run)
        print(f"{skill_name}: base={plan.base_dir}")
        for label, path in plan.canonical_dirs.items():
            print(f"  {label}: {path}")
        if args.dry_run:
            print("  mode: dry-run")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
