"""
core/path_builder.py — Config-Driven Canonical Path Construction
================================================================
Resolves all directory paths for a skill from its config.yaml `paths:` section.

Schema (all values relative to data/<skill_name>/):
    paths:
      input:  "input/..."        # canonical input root
      output: "output"           # canonical output root
      state:  "state"            # pipeline state JSON + checklist.md
      logs:   "logs"             # log files

      phases:                    # becomes self.dirs[key] in Phase scripts
        <key>: "relative/path"
        ...

Fallback:
    If config.yaml is missing or has no `paths:` section, PathBuilder
    falls back to the built-in defaults defined in _DEFAULTS so existing
    skills without a `paths:` block continue to work.

Zero `if skill_name ==` branches — any new skill only needs a
`paths:` section in its config.yaml.
"""

from __future__ import annotations

from functools import cached_property
import os
from typing import Dict

# ---------------------------------------------------------------------------
# Built-in defaults (used when config.yaml is unavailable).
# Structured identically to the YAML schema for consistency.
# ---------------------------------------------------------------------------
_DEFAULTS: Dict[str, Dict] = {
    "audio_transcriber": {
        "input": "input",
        "output": "output",
        "state": "state",
        "resume": "state/resume",
        "logs": "logs",
        "phases": {
            "p0": "input",
            "p1": "output/01_transcript",
            "p2": "output/02_proofread",
            "p3": "output/03_merged",
            "p4": "output/04_highlighted",
            "p5": "output/05_notion_synthesis",
        },
    },
    "doc_parser": {
        "input": "input",
        "output": "output",
        "state": "state",
        "resume": "state/resume",
        "logs": "logs",
        "phases": {
            "inbox": "input",
            "processed": "output/01_processed",
            "highlighted": "output/02_highlighted",
            "synthesis": "output/03_synthesis",
            "error": "output/error",
        },
    },
}

# Generic fallback for unknown skills with no config
_GENERIC_DEFAULT: Dict[str, str] = {
    "input": "input",
    "output": "output",
    "state": "state",
    "resume": "state/resume",
    "logs": "logs",
}


class PathBuilder:
    """
    Constructs absolute directory paths for an OpenClaw skill.

    Construction is cheap — YAML is loaded lazily on first access via
    `cached_property`. All derived paths are absolute strings.
    """

    def __init__(self, workspace_root: str, skill_name: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.skill_name = skill_name
        self.base_dir = os.path.join(self.workspace_root, "data", skill_name)

    # ------------------------------------------------------------------
    # Config loading (lazy, cached)
    # ------------------------------------------------------------------

    @cached_property
    def _raw_paths_cfg(self) -> Dict:
        """
        Load and return the `paths:` subtree from config.yaml, or fall
        back to the built-in defaults for this skill.
        """
        cfg_file = self.config_file  # skills/<skill>/config/config.yaml
        if os.path.exists(cfg_file):
            try:
                import yaml

                with open(cfg_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                paths_block = data.get("paths")
                if isinstance(paths_block, dict):
                    return paths_block
            except Exception:
                pass  # fall through to defaults

        # Config missing or has no `paths:` — use built-in defaults
        return _DEFAULTS.get(self.skill_name, _GENERIC_DEFAULT)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve(self, rel_path: str) -> str:
        """Join rel_path with base_dir, returning an absolute path."""
        return os.path.normpath(os.path.join(self.base_dir, rel_path))

    # ------------------------------------------------------------------
    # Static properties (no YAML needed)
    # ------------------------------------------------------------------

    @property
    def config_dir(self) -> str:
        return os.path.join(self.workspace_root, "skills", self.skill_name, "config")

    @property
    def config_file(self) -> str:
        return os.path.join(self.config_dir, "config.yaml")

    @property
    def prompt_file(self) -> str:
        return os.path.join(self.config_dir, "prompt.md")

    # ------------------------------------------------------------------
    # Config-driven path properties
    # ------------------------------------------------------------------

    @property
    def canonical_dirs(self) -> Dict[str, str]:
        """
        Returns the five canonical directories expected by PipelineBase:
        input, output, state, resume, logs.
        """
        cfg = self._raw_paths_cfg
        return {
            key: self._resolve(
                str(cfg.get(key, _DEFAULTS.get(self.skill_name, _GENERIC_DEFAULT).get(key)))
            )
            for key in ("input", "output", "state", "resume", "logs")
            if cfg.get(key) or _DEFAULTS.get(self.skill_name, _GENERIC_DEFAULT).get(key)
        }

    @property
    def phase_dirs(self) -> Dict[str, str]:
        """
        Returns the skill-specific phase directories from `paths.phases`.
        These become `self.dirs[key]` in every Phase script.
        """
        phases_cfg = self._raw_paths_cfg.get("phases", {})
        return {key: self._resolve(rel) for key, rel in phases_cfg.items()}

    @property
    def log_file(self) -> str:
        return os.path.join(self.canonical_dirs.get("logs", self.base_dir), "system.log")

    @property
    def state_file(self) -> str:
        return os.path.join(self.canonical_dirs.get("state", self.base_dir), ".pipeline_state.json")

    @property
    def checklist_file(self) -> str:
        return os.path.join(self.canonical_dirs.get("state", self.base_dir), "checklist.md")

    # ------------------------------------------------------------------
    # Directory creation
    # ------------------------------------------------------------------

    def ensure_directories(self) -> None:
        """Create all canonical and phase directories if they don't exist."""
        all_dirs = [
            self.base_dir,
            *self.canonical_dirs.values(),
            *self.phase_dirs.values(),
        ]
        for path in all_dirs:
            os.makedirs(path, exist_ok=True)

    # ------------------------------------------------------------------
    # Debug / introspection
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"PathBuilder(skill={self.skill_name!r}, base_dir={self.base_dir!r})"
