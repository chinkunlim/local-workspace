from datetime import datetime
import json
import os
import threading
from typing import Dict, Optional

from core.utils.atomic_writer import AtomicWriter

_manifest_lock = threading.Lock()


def update_session_manifest(
    workspace_root: str,
    subject: str,
    filename: str,
    skill: str,
    status: str,
    proofread_status: Optional[str] = None,
) -> Dict:
    """
    Atomically updates the .session_manifest.json for a given subject.
    """
    manifest_path = os.path.join(workspace_root, "data", "raw", subject, ".session_manifest.json")

    with _manifest_lock:
        os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
        manifest = {}
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception:
                pass

        manifest["subject"] = subject
        manifest["last_updated"] = datetime.now().isoformat()

        if "audio_files" not in manifest:
            manifest["audio_files"] = {}
        if "doc_files" not in manifest:
            manifest["doc_files"] = {}

        ext = os.path.splitext(filename)[1].lower()
        is_audio = ext in [".m4a", ".mp3", ".wav", ".ogg", ".aac", ".flac", ".opus"]

        target_dict = manifest["audio_files"] if is_audio else manifest["doc_files"]

        if filename not in target_dict:
            target_dict[filename] = {}

        target_dict[filename]["status"] = status
        target_dict[filename]["skill"] = skill

        if is_audio:
            if proofread_status:
                target_dict[filename]["proofread"] = proofread_status
            elif "proofread" not in target_dict[filename]:
                target_dict[filename]["proofread"] = "pending"

        AtomicWriter.write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))

        return manifest
