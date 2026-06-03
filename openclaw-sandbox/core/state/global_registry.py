import json
import os
import threading
from typing import Dict, Optional

from core.utils.atomic_writer import AtomicWriter


class GlobalRegistry:
    """
    Manages the global manifest of all processed assets across all skills.
    Stored at data/state/global_manifest.json.
    """

    _instances: Dict[str, "GlobalRegistry"] = {}
    _lock = threading.RLock()

    def __new__(cls, workspace_root: str = None):
        if not workspace_root:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            workspace_root = os.path.abspath(os.path.join(script_dir, "..", ".."))

        with cls._lock:
            if workspace_root not in cls._instances:
                instance = super().__new__(cls)
                instance._init(workspace_root)
                cls._instances[workspace_root] = instance
            return cls._instances[workspace_root]

    def _init(self, workspace_root: str):

        self.registry_path = os.path.join(workspace_root, "data", "state", "global_manifest.json")
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        self._memory_cache: Optional[Dict] = None

    def _load(self) -> Dict:
        if self._memory_cache is not None:
            return self._memory_cache

        if not os.path.exists(self.registry_path):
            self._memory_cache = {}
            return self._memory_cache

        try:
            with open(self.registry_path, encoding="utf-8") as f:
                self._memory_cache = json.load(f)
        except Exception:
            self._memory_cache = {}

        return self._memory_cache  # type: ignore[return-value]

    def _save(self):
        if self._memory_cache is not None:
            AtomicWriter.write_json(self.registry_path, self._memory_cache)

    def register_asset(self, subject: str, file_prefix: str, skill_name: str, filepath: str):
        """Register an asset path for a given subject, prefix, and skill.

        Supports multiple registrations for the same key: subsequent calls
        append to a list rather than overwriting, so doc_parser can register
        L02_1, L02_2, L02_3 all under prefix "L02".
        """
        with self._lock:
            data = self._load()

            if subject not in data:
                data[subject] = {}
            if file_prefix not in data[subject]:
                data[subject][file_prefix] = {}

            existing = data[subject][file_prefix].get(skill_name)
            if existing is None:
                data[subject][file_prefix][skill_name] = filepath
            elif isinstance(existing, list):
                if filepath not in existing:
                    existing.append(filepath)
            else:
                # Upgrade scalar → list on second registration
                if existing != filepath:
                    data[subject][file_prefix][skill_name] = [existing, filepath]
            self._save()

    def get_assets(self, subject: str, file_prefix: str) -> Dict[str, str]:
        """Returns all registered assets for a given file prefix."""
        with self._lock:
            data = self._load()
            return data.get(subject, {}).get(file_prefix, {})

    def get_asset_paths(self, subject: str, file_prefix: str, skill_name: str) -> list[str]:
        """Return registered paths for a skill as a flat list.
        Performs prefix matching so 'L13' matches 'L13 Myths' and 'L13_chapter'.
        """
        with self._lock:
            data = self._load()
            subject_data = data.get(subject, {})

            all_paths = []
            for key, skills_map in subject_data.items():
                if (
                    key == file_prefix
                    or key.startswith(f"{file_prefix} ")
                    or key.startswith(f"{file_prefix}_")
                    or key.startswith(f"{file_prefix}-")
                ):
                    raw = skills_map.get(skill_name)
                    if raw is not None:
                        if isinstance(raw, list):
                            all_paths.extend(raw)
                        else:
                            all_paths.append(raw)

            return list(dict.fromkeys(all_paths))

    def get_all_subjects(self) -> list:
        with self._lock:
            return list(self._load().keys())

    def get_subject_assets(self, subject: str) -> Dict[str, Dict[str, str]]:
        with self._lock:
            return self._load().get(subject, {})
