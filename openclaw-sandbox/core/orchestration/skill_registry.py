"""
core/skill_registry.py — Dynamic Plugin Discovery Architecture (#17)
====================================================================
Enables zero-friction extensibility: new Skills are auto-discovered
by scanning the skills/ directory at startup for a manifest.py file
that conforms to the SkillManifest protocol.

CURRENT STATUS: Fully functional discovery + registration.
  Async execution wiring (#16) and CLI/Telegram auto-population
  are the remaining P3 integration tasks.

Usage:
    from core.orchestration.skill_registry import SkillRegistry

    registry = SkillRegistry(skills_root="/path/to/skills")
    registry.discover()

    for name, manifest in registry.all().items():
        print(f"{name}: {manifest.description}")

    run_fn = registry.get_run_fn("audio_transcriber")
    run_fn(subject="math", force=False)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib.util
import os
import sys
from typing import Callable, Dict, List, Optional

from rich import print

# ---------------------------------------------------------------------------
# SkillManifest Protocol (#17)
# ---------------------------------------------------------------------------


@dataclass
class SkillManifest:
    """Interface contract every discoverable Skill must implement.

    Place a manifest.py in skills/<skill-name>/ that exposes a module-level
    variable named `MANIFEST` of this type.

    Example (skills/audio_transcriber/manifest.py):
        from core.orchestration.skill_registry import SkillManifest
        from scripts.run_all import VoiceMemoOrchestrator

        MANIFEST = SkillManifest(
            skill_name="audio_transcriber",
            description="Transcribe audio files using Whisper with anti-hallucination.",
            phases=["p0_glossary", "p1_transcribe", "p2_proofread", "p3_merge"],
            cli_entry="scripts/run_all.py",
            run_fn=lambda **kw: VoiceMemoOrchestrator().run(**kw),
            file_types=[".m4a", ".mp3", ".wav"],
        )
    """

    skill_name: str
    description: str
    phases: List[str] = field(default_factory=list)
    cli_entry: str = ""
    run_fn: Optional[Callable] = None
    file_types: List[str] = field(default_factory=list)  # e.g. [".m4a", ".pdf"]
    tags: List[str] = field(default_factory=list)  # e.g. ["audio", "transcription"]


# ---------------------------------------------------------------------------
# SkillRegistry
# ---------------------------------------------------------------------------


class SkillRegistry:
    """Discovers and registers Skills from the skills/ directory.

    Auto-discovery algorithm:
      For each subdirectory in skills_root:
        1. Look for a manifest.py file.
        2. Import it and extract the module-level MANIFEST variable.
        3. Register the SkillManifest under its skill_name.
    """

    def __init__(self, skills_root: Optional[str] = None):
        # Default to openclaw-sandbox/skills/ relative to this file
        if skills_root is None:
            skills_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills"))
        self.skills_root = skills_root
        self._registry: Dict[str, SkillManifest] = {}

    def discover(self) -> int:
        """Scan skills_root for manifest.py files and register them.

        Returns:
            Number of skills successfully registered.
        """
        if not os.path.isdir(self.skills_root):
            return 0

        discovered = 0
        for entry in sorted(os.listdir(self.skills_root)):
            skill_dir = os.path.join(self.skills_root, entry)
            manifest_path = os.path.join(skill_dir, "manifest.py")
            if not os.path.isfile(manifest_path):
                continue
            try:
                manifest = self._load_manifest(entry, manifest_path)
                if manifest:
                    self._registry[manifest.skill_name] = manifest
                    discovered += 1
            except Exception as exc:
                print(f"⚠️ [SkillRegistry] 無法載入 {entry}/manifest.py: {exc}")

        return discovered

    def _load_manifest(self, skill_dir_name: str, manifest_path: str) -> Optional[SkillManifest]:
        """Dynamically import a manifest.py and extract the MANIFEST variable."""
        module_name = f"openclaw_skill_{skill_dir_name.replace('-', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, manifest_path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod

        # Inject the skill directory so it can import its own internal modules
        skill_dir = os.path.dirname(manifest_path)
        sys.path.insert(0, skill_dir)
        try:
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
        finally:
            sys.path.remove(skill_dir)

        manifest = getattr(mod, "MANIFEST", None)
        if not isinstance(manifest, SkillManifest):
            raise TypeError(
                f"manifest.py must expose MANIFEST: SkillManifest, got {type(manifest)}"
            )
        return manifest

    def register(self, manifest: SkillManifest) -> None:
        """Manually register a SkillManifest (for testing or programmatic use)."""
        self._registry[manifest.skill_name] = manifest

    def get(self, skill_name: str) -> Optional[SkillManifest]:
        """Return a SkillManifest by name, or None if not found."""
        return self._registry.get(skill_name)

    def get_run_fn(self, skill_name: str) -> Callable:
        """Return the run callable for a skill, raising KeyError if missing."""
        manifest = self._registry.get(skill_name)
        if manifest is None:
            raise KeyError(
                f"Skill '{skill_name}' not registered. Run SkillRegistry.discover() first."
            )
        if manifest.run_fn is None:
            raise NotImplementedError(
                f"Skill '{skill_name}' has no run_fn defined in its manifest."
            )
        return manifest.run_fn

    def all(self) -> Dict[str, SkillManifest]:
        """Return a copy of the full registry."""
        return dict(self._registry)

    def list_names(self) -> List[str]:
        """Return sorted list of all registered skill names."""
        return sorted(self._registry.keys())

    def for_file_type(self, ext: str) -> List[SkillManifest]:
        """Return skills that can handle a given file extension."""
        return [m for m in self._registry.values() if ext.lower() in m.file_types]
