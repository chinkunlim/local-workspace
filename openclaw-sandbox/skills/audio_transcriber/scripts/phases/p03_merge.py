"""
Phase 3: Dialogue Merge
Refactored to purely merge transcript segments without LLM restructuring.
"""

import os
import re
import sys

# Internal Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import AtomicWriter, PipelineBase
from core.orchestration.event_bus import DomainEvent, EventBus
from core.state.global_registry import GlobalRegistry


class Phase3Merge(PipelineBase):
    def __init__(self) -> None:
        super().__init__(phase_key="p3", phase_name="順序合併", logger=None)

    def _get_lecture_base(self, fname: str) -> tuple[str, int | None]:
        stem = os.path.splitext(fname)[0]
        m = re.match(r"^(.+)-(\d+)$", stem)
        if m:
            return m.group(1), int(m.group(2))
        return stem, None

    def _group_tasks(self, tasks: list[dict]) -> dict[tuple[str, str], list[dict]]:
        groups: dict[tuple[str, str], list[dict]] = {}
        for task in tasks:
            base, _seg = self._get_lecture_base(task["filename"])
            key = (task["subject"], base)
            groups.setdefault(key, []).append(task)
        for key in groups:
            groups[key].sort(key=lambda t: self._get_lecture_base(t["filename"])[1] or 0)
        return groups

    def _batch_select_reprocess(self, done_tasks: list[dict]) -> dict[int, dict]:
        """Override: show one menu entry per lecture group, not per file.

        e.g., "L02  (2 段)" instead of "L02-1.m4a" and "L02-2.m4a".
        Selecting a group always includes ALL its segments (can't merge partial).
        """
        from core.cli.cli_menu import batch_select_tasks

        # Build group-level display list
        groups: dict[tuple, list] = {}
        for task in done_tasks:
            base, _seg = self._get_lecture_base(task["filename"])
            key = (task["subject"], base)
            groups.setdefault(key, []).append(task)

        group_display: list[dict] = []
        for (subj, base_name), seg_tasks in sorted(groups.items()):
            seg_tasks.sort(key=lambda t: self._get_lecture_base(t["filename"])[1] or 0)
            group_display.append(
                {
                    "subject": subj,
                    # Show the group name + segment count; cli_menu prints subject / filename
                    "filename": f"{base_name}  ({len(seg_tasks)} 段)",
                    "_tasks": seg_tasks,
                }
            )

        chosen_groups = batch_select_tasks(group_display, header="[P3] 已完成的合併群組")

        # Flatten selected groups → individual file tasks
        result: dict[int, dict] = {}
        idx = 0
        for group_item in chosen_groups.values():
            for task in group_item["_tasks"]:
                result[idx] = task
                idx += 1
        return result

    def run(
        self,
        force: bool = False,
        subject: str = None,
        file_filter: str = None,
        single_mode: bool = False,
        resume_from: dict = None,
    ) -> None:
        self.log("🧠 啟動 Phase 3：合併模式")

        tasks = self.get_tasks(
            prev_phase_key="p2",
            force=force,
            subject_filter=subject,
            file_filter=file_filter,
            single_mode=single_mode,
            resume_from=resume_from,
        )
        if not tasks:
            self.log("📋 Phase 3 沒有待處理的檔案。")
            return

        groups = self._group_tasks(tasks)
        self.log(f"📋 共有 {len(tasks)} 個檔案，歸屬於 {len(groups)} 個合併群組。")

        idx = 1
        for (subj, base_name), tasks_in_group in groups.items():
            if self.check_system_health():
                break

            self.log(f"📦 [{idx}/{len(groups)}] 正在合併：[{subj}] {base_name}")
            idx += 1

            merged_parts = []
            for task in tasks_in_group:
                fname = task["filename"]
                p2_path = os.path.join(self.dirs["p2"], subj, f"{os.path.splitext(fname)[0]}.md")

                if os.path.exists(p2_path):
                    with open(p2_path, encoding="utf-8") as f:
                        merged_parts.append(f.read().strip())
                else:
                    self.log(f"⚠️ 找不到套用檔：{p2_path}", "warn")

            if not merged_parts:
                continue

            # Pure merge with spacing
            final_doc = "\n\n".join(merged_parts)

            out_path = os.path.join(self.dirs["p3"], subj, f"{base_name}.md")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            AtomicWriter.write_text(out_path, final_doc)

            # --- Register in GlobalRegistry for proofreader ---
            prefix = base_name.split("_")[0] if "_" in base_name else base_name
            GlobalRegistry().register_asset(subj, prefix, "audio_transcriber", out_path)
            self.log(f"📋 已注冊至 GlobalRegistry: {prefix} → {out_path}")

            out_hash = self.state_manager.get_file_hash(out_path)
            for task in tasks_in_group:
                self.state_manager.update_task(
                    subj,
                    task["filename"],
                    "p3",
                    status="✅",
                    char_count=len(final_doc),
                    output_hash=out_hash,
                )
            self.log(f"✅ 合併完成：{base_name}.md")

            # --- Per-file EventBus Handoff ---
            workspace_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            EventBus.publish(
                DomainEvent(
                    name="PipelineCompleted",
                    source_skill="audio_transcriber",
                    payload={"filepath": out_path, "subject": subj, "chain": []},
                )
            )

            if self.stop_requested:
                break


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    args = parser.parse_args()
    Phase3Merge().run(force=args.force, subject=args.subject)
