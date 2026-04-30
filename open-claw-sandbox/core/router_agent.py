"""
core/router_agent.py — Cross-Skill Dynamic Orchestration (#13)
==============================================================
Strategic scaffold for the Router Agent, which chains multiple Skills
into automated end-to-end workflows based on file type and user intent.

CURRENT STATUS: Scaffold / Interface Definition
  This file defines the data contracts and orchestration skeleton.
  Actual skill invocation wiring is deferred to P3 implementation.

Usage (future):
    from core.router_agent import RouterAgent, TaskManifest

    manifest = TaskManifest(
        source_path="/path/to/lecture.m4a",
        intent="transcribe_and_compile",
    )
    RouterAgent().dispatch(manifest)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Data Contracts
# ---------------------------------------------------------------------------


@dataclass
class TaskManifest:
    """Describes a user-submitted task for the router to resolve."""

    source_path: str
    intent: str = "auto"  # e.g. "transcribe_and_compile", "parse_pdf", "study"
    subject: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class SkillCall:
    """A resolved step in the routing plan."""

    skill_name: str
    run_fn: Callable  # Callable that executes the skill
    description: str = ""


# ---------------------------------------------------------------------------
# Routing Table
# ---------------------------------------------------------------------------

# Maps (file_extension, intent) → ordered list of SkillCall names.
# Populated at registration time by SkillRegistry (#17).
_ROUTING_TABLE: Dict[str, List[str]] = {
    ".m4a:auto": ["audio-transcriber", "note_generator", "knowledge-compiler"],
    ".mp3:auto": ["audio-transcriber", "note_generator", "knowledge-compiler"],
    ".pdf:auto": ["doc-parser", "note_generator", "knowledge-compiler"],
    ".pdf:study": ["doc-parser", "academic-edu-assistant"],
    ".md:compile": ["knowledge-compiler"],
}


# ---------------------------------------------------------------------------
# Router Agent
# ---------------------------------------------------------------------------


class RouterAgent:
    """Central routing intelligence for the Open Claw multi-skill pipeline.

    Resolves a TaskManifest into an ordered sequence of SkillCalls and
    executes them in order. On skill failure, logs the error and (optionally)
    triggers the HITL protocol for human intervention.
    """

    def __init__(self, registry=None):
        # registry: SkillRegistry instance injected at runtime (#17)
        self._registry = registry

    def resolve(self, manifest: TaskManifest) -> List[str]:
        """Resolve a manifest to an ordered list of skill names."""
        ext = os.path.splitext(manifest.source_path)[-1].lower()
        key = f"{ext}:{manifest.intent}"
        fallback_key = f"{ext}:auto"
        chain = _ROUTING_TABLE.get(key) or _ROUTING_TABLE.get(fallback_key) or []
        return chain

    def dispatch(self, manifest: TaskManifest, dry_run: bool = False) -> Dict:
        """Dispatch a TaskManifest through the resolved skill chain.

        Args:
            manifest: The incoming task specification.
            dry_run:  If True, print the plan without executing.

        Returns:
            dict with keys: "plan" (list of skill names), "results" (list of outcomes)
        """
        chain = self.resolve(manifest)
        results = []

        print(f"🗺️  [RouterAgent] 路由計畫: {' → '.join(chain) or '(無匹配路由)'}")

        if dry_run or not chain:
            return {"plan": chain, "results": []}

        for skill_name in chain:
            if self._registry is None:
                results.append({"skill": skill_name, "status": "skipped", "reason": "no registry"})
                continue
            try:
                run_fn = self._registry.get_run_fn(skill_name)
                run_fn(subject=manifest.subject)
                results.append({"skill": skill_name, "status": "success"})
            except Exception as exc:
                results.append({"skill": skill_name, "status": "error", "error": str(exc)})
                print(f"❌ [RouterAgent] {skill_name} 失敗: {exc}")
                break  # Stop chain on failure; HITL (#14) would resume here

        return {"plan": chain, "results": results}
