import os
import sys

# Ensure workspace root is in path
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from core.orchestration.event_bus import DomainEvent, EventBus
from core.orchestration.router_agent import RouterAgent, TaskManifest
from core.orchestration.skill_registry import SkillRegistry
from core.orchestration.task_queue import LocalTaskQueue


class MockTaskQueue(LocalTaskQueue):
    def _init(self):
        self.dispatched_tasks = []

    def enqueue(
        self, name, cmd, cwd, filepath=None, skill=None, chain=None, subject="Default", env=None
    ):
        self.dispatched_tasks.append(
            {"name": name, "cmd": cmd, "skill": skill, "chain": chain, "filepath": filepath}
        )
        print(f"✅ Enqueued Task: {name}")
        print(f"  └─ Skill: {skill}")
        print(f"  └─ Chain: {chain}")
        print(f"  └─ Target File: {filepath}")
        print(f"  └─ Command: {' '.join(cmd)}")
        print()


def run_simulation():
    print("🚀 啟動 RouterAgent 路由模擬測試...\n")

    # 1. Setup mocks
    import core.orchestration.router_agent

    mock_queue = MockTaskQueue()
    core.orchestration.router_agent.task_queue = mock_queue

    registry = SkillRegistry(os.path.join(workspace_root, "skills"))
    registry.discover()
    router = RouterAgent(registry=registry)

    # 2. Simulate File Ingestion
    print("=== 測試 1: 匯入 .md:research (研究點子) ===")
    manifest = TaskManifest(
        source_path="/fake/path/idea.md", subject="Incubator", intent="research"
    )
    chain = router.resolve(manifest)
    print(f"解析管線: {chain}")

    # Simulate moving file
    target_dir = os.path.join(workspace_root, "data", "student_researcher", "input", "Incubator")
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, "idea.md")
    with open(target_path, "w") as f:
        f.write("Dummy")

    manifest.source_path = target_path
    router.dispatch(manifest)

    print("\n=== 測試 2: 模擬 student_researcher 完成，測試泛用交棒 (Universal Handoff) ===")
    mock_queue.dispatched_tasks.clear()
    event = DomainEvent(
        name="PipelineCompleted",
        source_skill="student_researcher",
        payload={"filepath": target_path, "chain": chain, "subject": "Incubator"},
    )
    router._on_pipeline_completed(event)

    print("\n=== 測試 3: 匯入 .mkv (影片攝取) ===")
    manifest2 = TaskManifest(
        source_path="/fake/path/lecture.mkv", subject="CourseA", intent="ingest"
    )
    chain2 = router.resolve(manifest2)
    print(f"解析管線: {chain2}")


if __name__ == "__main__":
    run_simulation()
