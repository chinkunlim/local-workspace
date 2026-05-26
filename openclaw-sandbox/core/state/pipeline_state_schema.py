"""
core/state/pipeline_state_schema.py
===================================
Provides structured Dataclasses for .pipeline_state.json.
This ensures type safety when reading/writing state files instead of raw dict access.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from typing import Any, Dict


@dataclass
class PhaseStatus:
    status: str = "pending"
    note: str = ""


@dataclass
class TaskRecord:
    subject: str
    filename: str
    phases: Dict[str, PhaseStatus] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskRecord:
        phases = {
            k: PhaseStatus(**v) if isinstance(v, dict) else PhaseStatus(status=v)
            for k, v in data.get("phases", {}).items()
        }
        return cls(
            subject=data.get("subject", ""), filename=data.get("filename", ""), phases=phases
        )


@dataclass
class PipelineStateSnapshot:
    tasks: Dict[str, TaskRecord] = field(default_factory=dict)

    @classmethod
    def load(cls, state_file_path: str) -> PipelineStateSnapshot:
        if not os.path.exists(state_file_path):
            return cls()

        try:
            with open(state_file_path, encoding="utf-8") as f:
                data = json.load(f)

            tasks = {k: TaskRecord.from_dict(v) for k, v in data.get("tasks", {}).items()}
            return cls(tasks=tasks)
        except Exception:
            return cls()

    def save(self, state_file_path: str) -> None:
        from core.utils.atomic_writer import AtomicWriter

        data = asdict(self)
        AtomicWriter.write_json(state_file_path, data)
