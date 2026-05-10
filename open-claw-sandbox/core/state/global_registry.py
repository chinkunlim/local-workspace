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

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, workspace_root: str = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GlobalRegistry, cls).__new__(cls)
                cls._instance._init(workspace_root)
            return cls._instance

    def _init(self, workspace_root: str = None):
        if not workspace_root:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            workspace_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
            
        self.registry_path = os.path.join(workspace_root, "data", "state", "global_manifest.json")
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        self._memory_cache = None

    def _load(self) -> Dict:
        if self._memory_cache is not None:
            return self._memory_cache
            
        if not os.path.exists(self.registry_path):
            self._memory_cache = {}
            return self._memory_cache

        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                self._memory_cache = json.load(f)
        except Exception:
            self._memory_cache = {}
            
        return self._memory_cache

    def _save(self):
        if self._memory_cache is not None:
            AtomicWriter.write_json(self.registry_path, self._memory_cache)

    def register_asset(self, subject: str, file_prefix: str, skill_name: str, filepath: str):
        """
        Registers an asset for a given subject and file prefix.
        file_prefix should be the base name without extensions or suffix markers.
        """
        with self._lock:
            data = self._load()
            
            if subject not in data:
                data[subject] = {}
                
            if file_prefix not in data[subject]:
                data[subject][file_prefix] = {}
                
            data[subject][file_prefix][skill_name] = filepath
            self._save()

    def get_assets(self, subject: str, file_prefix: str) -> Dict[str, str]:
        """Returns all registered assets for a given file prefix."""
        with self._lock:
            data = self._load()
            return data.get(subject, {}).get(file_prefix, {})
            
    def get_all_subjects(self) -> list:
        with self._lock:
            return list(self._load().keys())
            
    def get_subject_assets(self, subject: str) -> Dict[str, Dict[str, str]]:
        with self._lock:
            return self._load().get(subject, {})

