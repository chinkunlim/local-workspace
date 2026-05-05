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
import sys
from typing import Callable, Dict, List, Optional

from core.cli.cli_runner import SkillRunner
from core.orchestration.event_bus import DomainEvent, EventBus
from core.orchestration.task_queue import task_queue

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
    model: Optional[str] = None


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
    ".m4a:auto": [
        "audio_transcriber",
        "note_generator",
        "student_researcher",
        "academic_library_agent",
        "gemini_verifier_agent",
        "knowledge_compiler",
    ],
    ".mp3:auto": [
        "audio_transcriber",
        "note_generator",
        "student_researcher",
        "academic_library_agent",
        "gemini_verifier_agent",
        "knowledge_compiler",
    ],
    ".pdf:auto": [
        "doc_parser",
        "note_generator",
        "student_researcher",
        "academic_library_agent",
        "gemini_verifier_agent",
        "knowledge_compiler",
    ],
    ".pdf:study": ["doc_parser", "academic_edu_assistant"],
    ".md:compile": ["knowledge_compiler"],
    ".md:research": [
        "student_researcher",
        "academic_library_agent",
        "gemini_verifier_agent",
        "knowledge_compiler",
    ],
    ".md:feynman": [
        "feynman_simulator",
        "knowledge_compiler",
    ],
    ".mp4:ingest": [
        "video_ingester",
        "note_generator",
        "student_researcher",
        "academic_library_agent",
        "gemini_verifier_agent",
        "knowledge_compiler",
    ],
    ".mov:ingest": ["video_ingester", "note_generator", "knowledge_compiler"],
    ".mkv:ingest": ["video_ingester", "note_generator", "knowledge_compiler"],
    ".webm:ingest": ["video_ingester", "note_generator", "knowledge_compiler"],
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

        # Subscribe to EventBus to continue chains
        EventBus.subscribe("PipelineCompleted", self._on_pipeline_completed)

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
            "- student_researcher: 萃取需要學術查證的論點\n"
            "- academic_library_agent: 操作 Playwright 抓取 Elsevier/ScienceDirect 文獻\n"
            "- gemini_verifier_agent: 與 Gemini 進行 AI-to-AI 辯證與查證\n"
            "- feynman_simulator: 模擬費曼學習法，進行師生 AI 辯證\n"
            "- knowledge_compiler: 將筆記編譯進知識庫並做雙向連結\n"
            "- telegram_kb_agent: 提供知識庫問答\n"
            "- video_ingester: 擷取影片關鍵影格並將語音轉為文字\n\n"
            "請將任務拆解為執行順序清單，只輸出技能名稱，以逗號分隔，例如：\n"
            "audio_transcriber,note_generator,knowledge_compiler"
        )
        try:
            # Use the complexity-selected model for routing decomposition only.
            # This does NOT affect downstream skills, which use their own config.yaml models.
            routing_model = os.environ.get("OPENCLAW_ROUTER_MODEL", "qwen3:8b")
            raw = self._llm.generate(model=routing_model, prompt=prompt)
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
                    "student_researcher",
                    "academic_library_agent",
                    "gemini_verifier_agent",
                    "feynman_simulator",
                ]
            ]
        except Exception as e:
            print(f"⚠️ [RouterAgent] LLM 分解任務失敗: {e}")
            return []

    def resolve(self, manifest: TaskManifest) -> List[str]:
        """Resolve a manifest to an ordered list of skill names."""
        ext = os.path.splitext(manifest.source_path)[-1].lower()

        # Context-Aware Model Routing (P4)
        complex_keywords = ["debate", "research", "feynman", "analyze", "deep", "study"]
        if any(k in manifest.intent.lower() for k in complex_keywords):
            manifest.model = "qwen3:14b"  # high-complexity: strong multilingual reasoning
        else:
            manifest.model = "qwen3:8b"  # low-complexity: fast, efficient

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

    def _on_pipeline_completed(self, event: DomainEvent) -> None:
        """Handle EventBus handoff to trigger the next skill in the chain."""
        payload = event.payload
        chain = payload.get("chain", [])

        if len(chain) <= 1:
            print(f"🏁 [RouterAgent] 整個路由計畫已完成: {event.source_skill}")
            return

        # The chain has remaining skills. The next skill is at index 1.
        current_skill = chain[0]
        next_skill = chain[1]
        remaining_chain = chain[1:]
        subject = payload.get("subject", "Default")
        filepath = payload.get("filepath", "")
        file_id = os.path.splitext(os.path.basename(filepath))[0]
        model = payload.get("model") or "qwen3:8b"
        env = {"OPENCLAW_ROUTER_MODEL": model}

        print(f"🗺️  [RouterAgent] 接力觸發: {current_skill} -> {next_skill} (Model: {model})")

        try:
            # Auto-discover the output of current_skill to use as input for next_skill
            # We assume next_skill is note-generator or knowledge_compiler
            # In V8 architecture, SkillRunner provides standard resolution.
            if next_skill == "note_generator":
                input_path, output_path = SkillRunner.resolve_synthesize_paths(
                    current_skill, subject, file_id
                )
                cmd = SkillRunner.run_note_generator(
                    input_file=input_path, output_file=output_path, subject=subject
                )
                cwd = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    "skills",
                    "note_generator",
                )
                task_queue.enqueue(
                    name=f"Note Generator Pipeline ({subject})",
                    cmd=cmd,
                    cwd=cwd,
                    filepath=input_path,
                    skill="note_generator",
                    chain=remaining_chain,
                    subject=subject,
                    env=env,
                )
            elif next_skill == "knowledge_compiler":
                # For knowledge_compiler, the input is just the subject/file from the previous step.
                cmd = [sys.executable, "scripts/run_all.py", "--subject", subject]
                cwd = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    "skills",
                    "knowledge_compiler",
                )
                task_queue.enqueue(
                    name=f"Knowledge Compiler Pipeline ({subject})",
                    cmd=cmd,
                    cwd=cwd,
                    filepath=filepath,
                    skill="knowledge_compiler",
                    chain=remaining_chain,
                    subject=subject,
                    env=env,
                )
            elif next_skill in [
                "student_researcher",
                "academic_library_agent",
                "gemini_verifier_agent",
                "feynman_simulator",
            ]:
                # These skills use the unified interface
                cmd = [sys.executable, "scripts/run_all.py", "--subject", subject]
                cwd = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    "skills",
                    next_skill,
                )
                task_queue.enqueue(
                    name=f"{next_skill} ({subject})",
                    cmd=cmd,
                    cwd=cwd,
                    filepath=filepath,
                    skill=next_skill,
                    chain=remaining_chain,
                    subject=subject,
                    env=env,
                )
            else:
                print(f"⚠️ [RouterAgent] 尚不支援自動接力到 {next_skill}，請手動觸發。")

        except Exception as e:
            print(f"❌ [RouterAgent] 接力失敗: {e}")

    def dispatch(self, manifest: TaskManifest, dry_run: bool = False) -> Dict:
        """Dispatch a TaskManifest through the resolved skill chain."""
        chain = self.resolve(manifest)
        results = []

        print(f"🗺️  [RouterAgent] 路由計畫: {' → '.join(chain) or '(無匹配路由)'}")

        if dry_run or not chain:
            return {"plan": chain, "results": []}

        # Event-driven architecture: we ONLY enqueue the first skill in the chain.
        # The subsequent skills are triggered via EventBus by the skill's manifest listener.
        # But wait, RouterAgent only routes the file to the first skill's input directory,
        # then enqueues the first skill.
        first_skill = chain[0]
        if self._registry is None:
            results.append({"skill": first_skill, "status": "skipped", "reason": "no registry"})
            return {"plan": chain, "results": results}

        try:
            skill_manifest = self._registry.get(first_skill)
            if not skill_manifest:
                raise KeyError(f"Skill '{first_skill}' not found in registry.")

            # Route the physical file
            target_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "data",
                first_skill,
                "input",
                manifest.subject or "Default",
            )
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, os.path.basename(manifest.source_path))

            # Move file if it's not already there
            if manifest.source_path != target_path:
                os.rename(manifest.source_path, target_path)

            cwd = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "skills",
                first_skill,
            )

            # Build command from cli_entry or fallback
            if skill_manifest.cli_entry:
                script_path = os.path.join(cwd, skill_manifest.cli_entry)
            else:
                script_path = os.path.join(cwd, "scripts", "run_all.py")

            cmd = [sys.executable, script_path]
            # Some skills expect --process-all (e.g. doc_parser)
            if first_skill == "doc_parser":
                cmd.append("--process-all")

            task_queue.enqueue(
                name=f"{first_skill} Pipeline",
                cmd=cmd,
                cwd=cwd,
                filepath=target_path,
                skill=first_skill,
                chain=chain,
                subject=manifest.subject or "Default",
                env={"OPENCLAW_ROUTER_MODEL": manifest.model} if manifest.model else None,
            )

            results.append({"skill": first_skill, "status": "enqueued"})
        except Exception as exc:
            results.append({"skill": first_skill, "status": "error", "error": str(exc)})
            print(f"❌ [RouterAgent] {first_skill} 分發失敗: {exc}")

        return {"plan": chain, "results": results}
