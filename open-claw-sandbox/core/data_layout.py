# -*- coding: utf-8 -*-
"""Canonical data-layout migration helpers.

These helpers preserve existing phase paths by creating symlinks to the new
input/output/state/logs structure when possible.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class DataLayoutPlan:
    skill_name: str
    base_dir: str
    canonical_dirs: Dict[str, str]
    legacy_aliases: Dict[str, str]


class DataLayoutManager:
    @staticmethod
    def plan(workspace_root: str, skill_name: str) -> DataLayoutPlan:
        base_dir = os.path.join(os.path.abspath(workspace_root), "data", skill_name)

        if skill_name == "audio-transcriber":
            canonical_dirs = {
                "input": os.path.join(base_dir, "input"),
                "output": os.path.join(base_dir, "output"),
                "state": os.path.join(base_dir, "state"),
                "resume": os.path.join(base_dir, "state", "resume"),
                "logs": os.path.join(base_dir, "logs"),
            }
            legacy_aliases = {
                os.path.join(base_dir, "raw_data"): canonical_dirs["input"],
                os.path.join(base_dir, "01_transcript"): os.path.join(canonical_dirs["output"], "01_transcript"),
                os.path.join(base_dir, "02_proofread"): os.path.join(canonical_dirs["output"], "02_proofread"),
                os.path.join(base_dir, "03_merged"): os.path.join(canonical_dirs["output"], "03_merged"),
                os.path.join(base_dir, "04_highlighted"): os.path.join(canonical_dirs["output"], "04_highlighted"),
                os.path.join(base_dir, "05_notion_synthesis"): os.path.join(canonical_dirs["output"], "05_notion_synthesis"),
                os.path.join(base_dir, ".pipeline_state.json"): os.path.join(canonical_dirs["state"], ".pipeline_state.json"),
                os.path.join(base_dir, "checklist.md"): os.path.join(canonical_dirs["state"], "checklist.md"),
                os.path.join(base_dir, "system.log"): os.path.join(canonical_dirs["logs"], "system.log"),
            }
        elif skill_name == "doc-parser":
            canonical_dirs = {
                "input": os.path.join(base_dir, "input"),
                "output": os.path.join(base_dir, "output"),
                "state": os.path.join(base_dir, "state"),
                "resume": os.path.join(base_dir, "state", "resume"),
                "logs": os.path.join(base_dir, "logs"),
            }
            # Migration complete: no legacy aliases needed.
            # All code now references canonical paths directly.
            legacy_aliases: Dict[str, str] = {}
        else:
            canonical_dirs = {
                "input": os.path.join(base_dir, "input"),
                "output": os.path.join(base_dir, "output"),
                "state": os.path.join(base_dir, "state"),
                "resume": os.path.join(base_dir, "state", "resume"),
                "logs": os.path.join(base_dir, "logs"),
            }
            legacy_aliases = {}

        return DataLayoutPlan(skill_name, base_dir, canonical_dirs, legacy_aliases)

    @staticmethod
    def migrate(workspace_root: str, skill_name: str, *, dry_run: bool = False) -> DataLayoutPlan:
        plan = DataLayoutManager.plan(workspace_root, skill_name)

        for path in plan.canonical_dirs.values():
            if not dry_run:
                os.makedirs(path, exist_ok=True)

        for alias_path, canonical_path in plan.legacy_aliases.items():
            if os.path.islink(alias_path):
                continue

            if os.path.isdir(alias_path) and not os.path.isdir(canonical_path):
                if not dry_run:
                    os.makedirs(os.path.dirname(canonical_path), exist_ok=True)
                    shutil.move(alias_path, canonical_path)
            elif os.path.isfile(alias_path) and not os.path.exists(canonical_path):
                if not dry_run:
                    os.makedirs(os.path.dirname(canonical_path), exist_ok=True)
                    shutil.move(alias_path, canonical_path)

            if not dry_run:
                if os.path.exists(alias_path):
                    if os.path.isdir(alias_path) and not os.path.islink(alias_path):
                        shutil.rmtree(alias_path)
                    else:
                        os.unlink(alias_path)
                os.makedirs(os.path.dirname(alias_path), exist_ok=True)
                os.symlink(canonical_path, alias_path)

        return plan
