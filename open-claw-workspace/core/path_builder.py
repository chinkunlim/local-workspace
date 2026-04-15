# -*- coding: utf-8 -*-
"""Canonical path construction for OpenClaw skills."""

from __future__ import annotations

import os
from typing import Dict


class PathBuilder:
    def __init__(self, workspace_root: str, skill_name: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.skill_name = skill_name
        self.base_dir = os.path.join(self.workspace_root, "data", skill_name)

    @property
    def config_dir(self) -> str:
        return os.path.join(self.workspace_root, "skills", self.skill_name, "config")

    @property
    def config_file(self) -> str:
        return os.path.join(self.config_dir, "config.yaml")

    @property
    def prompt_file(self) -> str:
        return os.path.join(self.config_dir, "prompt.md")

    @property
    def log_file(self) -> str:
        return os.path.join(self.canonical_dirs["logs"], "system.log")

    @property
    def state_file(self) -> str:
        return os.path.join(self.canonical_dirs["state"], ".pipeline_state.json")

    @property
    def checklist_file(self) -> str:
        return os.path.join(self.canonical_dirs["state"], "checklist.md")

    @property
    def canonical_dirs(self) -> Dict[str, str]:
        if self.skill_name == "voice-memo":
            return {
                "input": os.path.join(self.base_dir, "input", "raw_data"),
                "output": os.path.join(self.base_dir, "output"),
                "state": os.path.join(self.base_dir, "state"),
                "logs": os.path.join(self.base_dir, "logs"),
            }
        if self.skill_name == "pdf-knowledge":
            return {
                "input": os.path.join(self.base_dir, "input", "01_Inbox"),
                "output": os.path.join(self.base_dir, "output"),
                "state": os.path.join(self.base_dir, "state"),
                "logs": os.path.join(self.base_dir, "logs"),
            }
        return {
            "input": self.base_dir,
            "output": self.base_dir,
            "state": self.base_dir,
            "logs": self.base_dir,
        }

    @property
    def phase_dirs(self) -> Dict[str, str]:
        if self.skill_name == "voice-memo":
            return {
                "p0": os.path.join(self.base_dir, "raw_data"),
                "p1": os.path.join(self.base_dir, "01_transcript"),
                "p2": os.path.join(self.base_dir, "02_proofread"),
                "p3": os.path.join(self.base_dir, "03_merged"),
                "p4": os.path.join(self.base_dir, "04_highlighted"),
                "p5": os.path.join(self.base_dir, "05_notion_synthesis"),
            }
        if self.skill_name == "pdf-knowledge":
            return {
                "inbox": os.path.join(self.base_dir, "01_Inbox"),
                "processed": os.path.join(self.base_dir, "02_Processed"),
                "agent_core": os.path.join(self.base_dir, "03_Agent_Core"),
                "final": os.path.join(self.base_dir, "05_Final_Knowledge"),
                "error": os.path.join(self.base_dir, "Error"),
            }
        return {}

    def ensure_directories(self) -> None:
        canonical_values = list(self.canonical_dirs.values())
        for path in [self.base_dir, *canonical_values, *self.phase_dirs.values()]:
            os.makedirs(path, exist_ok=True)