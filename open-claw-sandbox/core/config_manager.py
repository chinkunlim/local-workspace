# -*- coding: utf-8 -*-
"""Centralized skill configuration loading."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigManager:
    def __init__(self, workspace_root: str, skill_name: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.skill_name = skill_name
        self.config_dir = Path(self.workspace_root) / "skills" / skill_name / "config"
        self.config_file = self.config_dir / "config.yaml"
        self.global_config_file = Path(self.workspace_root) / "core" / "config" / "global.yaml"
        self.data = self._load()

    def _expand_placeholders(self, value: Any) -> Any:
        if isinstance(value, str):
            return value.replace("${WORKSPACE_DIR}", self.workspace_root)
        if isinstance(value, dict):
            return {key: self._expand_placeholders(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._expand_placeholders(item) for item in value]
        return value

    def _load(self) -> Dict[str, Any]:
        # 1. Load global base config
        merged: Dict[str, Any] = {}
        if self.global_config_file.exists():
            with self.global_config_file.open("r", encoding="utf-8") as handle:
                global_raw = yaml.safe_load(handle) or {}
            merged = self._expand_placeholders(global_raw)

        # 2. Deep-merge skill-specific config on top
        if self.config_file.exists():
            with self.config_file.open("r", encoding="utf-8") as handle:
                skill_raw = yaml.safe_load(handle) or {}
            skill_data = self._expand_placeholders(skill_raw)
            merged = self._deep_merge(merged, skill_data)

        return merged

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge override into base, returning a new dict."""
        result = dict(base)
        for key, val in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(val, dict):
                result[key] = ConfigManager._deep_merge(result[key], val)
            else:
                result[key] = val
        return result

    def reload(self) -> Dict[str, Any]:
        self.data = self._load()
        return self.data

    def get_section(self, section_name: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        section = self.data.get(section_name, default or {})
        return section if isinstance(section, dict) else (default or {})

    def get_profile(
        self,
        section_name: str,
        subject_name: Optional[str] = None,
        default: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        section = self.get_section(section_name, {})
        profiles = section.get("profiles", {})
        if not isinstance(profiles, dict):
            return default or {}

        active_profile = section.get("active_profile", "default")
        if subject_name:
            overrides = section.get("subject_overrides", {})
            if isinstance(overrides, dict) and subject_name in overrides:
                active_profile = overrides[subject_name]

        profile = profiles.get(active_profile)
        if profile is None:
            return default or {}
        return profile if isinstance(profile, dict) else (default or {})

    def get_nested(self, *keys: str, default: Any = None) -> Any:
        node: Any = self.data
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node