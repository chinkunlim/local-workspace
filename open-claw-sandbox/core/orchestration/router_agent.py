"""
core/router_agent.py — Cross-Skill Dynamic Orchestration (#13)
==============================================================
Strategic scaffold for the Router Agent, which chains multiple Skills
into automated end-to-end workflows based on file type and user intent.

CURRENT STATUS: Scaffold / Interface Definition
  This file defines the data contracts and orchestration skeleton.
  Actual skill invocation wiring is deferred to P3 implementation.

Usage (future):
    from core.orchestration.router_agent import RouterAgent, TaskManifest

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
    ".m4a:auto": ["audio_transcriber", "note_generator", "knowledge_compiler"],
    ".mp3:auto": ["audio_transcriber", "note_generator", "knowledge_compiler"],
    ".pdf:auto": ["doc_parser", "note_generator", "knowledge_compiler"],
    ".pdf:study": ["doc_parser", "academic_edu_assistant"],
    ".md:compile": ["knowledge_compiler"],
}


# ---------------------------------------------------------------------------
# Router Agent
# ---------------------------------------------------------------------------


class RouterAgent:
    """Central routing intelligence for the Open Claw multi-skill pipeline (P4.1).

    Resolves a TaskManifest into an ordered sequence of SkillCalls and
    executes them in order. Can use LLM to decompose natural language intents
    into a DAG/Pipeline of skills.
    """

    def __init__(self, registry=None, llm_client=None):
        # registry: SkillRegistry instance injected at runtime
        self._registry = registry
        self._llm = llm_client

    def _llm_decompose(self, intent: str, ext: str) -> List[str]:
        """Use LLM to decompose a natural language request into a skill pipeline."""
        if not self._llm:
            return []
        prompt = (
            f"使用者意圖: {intent}\n"
            f"檔案類型: {ext}\n\n"
            "我們有以下技能：\n"
            "- audio_transcriber: 將語音轉為文字\n"
            "- doc_parser: 將 PDF 解析為文字\n"
            "- note_generator: 根據文字產生摘要與筆記\n"
            "- knowledge_compiler: 將筆記編譯進知識庫並做雙向連結\n"
            "- telegram_kb_agent: 提供知識庫問答\n\n"
            "請將任務拆解為執行順序清單，只輸出技能名稱，以逗號分隔，例如：\n"
            "audio_transcriber,note_generator,knowledge_compiler"
        )
        try:
            # We use a fast/smart model for routing if available, else default
            raw = self._llm.generate(model="qwen2.5-coder:7b", prompt=prompt)
            skills = [s.strip() for s in raw.split(",") if s.strip()]
            return [
                s
                for s in skills
                if s
                in [
                    "audio_transcriber",
                    "doc_parser",
                    "note_generator",
                    "knowledge_compiler",
                    "telegram_kb_agent",
                    "academic_edu_assistant",
                ]
            ]
        except Exception as e:
            print(f"⚠️ [RouterAgent] LLM 分解任務失敗: {e}")
            return []

    def resolve(self, manifest: TaskManifest) -> List[str]:
        """Resolve a manifest to an ordered list of skill names."""
        ext = os.path.splitext(manifest.source_path)[-1].lower()

        # 1. Natural language decomposition if intent is not a simple keyword
        if manifest.intent not in ["auto", "study", "compile"] and len(manifest.intent) > 10:
            llm_chain = self._llm_decompose(manifest.intent, ext)
            if llm_chain:
                return llm_chain

        # 2. Rule-based fallback
        key = f"{ext}:{manifest.intent}"
        fallback_key = f"{ext}:auto"
        chain = _ROUTING_TABLE.get(key) or _ROUTING_TABLE.get(fallback_key) or []
        return chain

    def dispatch(self, manifest: TaskManifest, dry_run: bool = False) -> Dict:
        """Dispatch a TaskManifest through the resolved skill chain."""
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
                # Pass intent metadata to the skill if it supports it
                kwargs = {"subject": manifest.subject}
                run_fn(**kwargs)
                results.append({"skill": skill_name, "status": "success"})
            except Exception as exc:
                results.append({"skill": skill_name, "status": "error", "error": str(exc)})
                print(f"❌ [RouterAgent] {skill_name} 失敗: {exc}")
                break

        return {"plan": chain, "results": results}
