"""
Phase 2: Document Completeness
Compares proofread transcript against doc_parser reference, embeds images, and flags missing concepts.
"""

import json
import os
import sys

# Internal Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import AtomicWriter, PipelineBase
from core.orchestration.event_bus import DomainEvent, EventBus
from core.state.global_registry import GlobalRegistry
from core.utils.text_utils import smart_split


class Phase3DocCompleteness(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p3", phase_name="Doc Completeness", skill_name="proofreader")

    def _workspace_root(self) -> str:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

    def _get_reference_data(self, subject: str, prefix: str) -> tuple[str, str]:
        """Fetch doc_parser reference text and figure list for this prefix.

        Reads all paths registered under (subject, prefix, "doc_parser") in GlobalRegistry.
        For each path, also looks for a sibling figure_list.md in the same directory.
        """
        registry = GlobalRegistry(self._workspace_root())
        paths = registry.get_asset_paths(subject, prefix, "doc_parser")

        ref_parts: list[str] = []
        fig_parts: list[str] = []

        for p in paths:
            if not os.path.exists(p):
                continue
            try:
                with open(p, encoding="utf-8") as f:
                    ref_parts.append(f.read()[:6000])
            except Exception:
                pass

            fig_path = os.path.join(os.path.dirname(p), "figure_list.md")
            if os.path.exists(fig_path):
                try:
                    with open(fig_path, encoding="utf-8") as f:
                        fig_parts.append(f.read())
                except Exception:
                    pass

        ref_text = ("\n\n---\n\n".join(ref_parts))[:20000]
        figure_list_text = "\n\n".join(fig_parts)
        return ref_text, figure_list_text

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.log("🧠 啟動 Phase 3：Doc Completeness")

        self._p2_dir = self.dirs.get(
            "p2", os.path.join(self.base_dir, "output", "02_transcript_proofread")
        )
        self.state_manager.raw_dir = self._p2_dir

        with self.state_manager._lock:
            if os.path.exists(self._p2_dir):
                subjects = (
                    [subject]
                    if subject
                    else [
                        d
                        for d in os.listdir(self._p2_dir)
                        if os.path.isdir(os.path.join(self._p2_dir, d))
                    ]
                )
                for subj in subjects:
                    subj_dir = os.path.join(self._p2_dir, subj)
                    if not os.path.isdir(subj_dir):
                        continue
                    if subj not in self.state_manager.state:
                        self.state_manager.state[subj] = {}
                    for fname in os.listdir(subj_dir):
                        if not fname.endswith(".md") or fname == "correction_log.md":
                            continue
                        if fname not in self.state_manager.state[subj]:
                            self.state_manager.state[subj][fname] = {
                                **dict.fromkeys(self.state_manager.PHASES, "⏳"),
                                "p1": "⏭️",
                                "hash": "",
                                "date": "",
                                "note": "",
                                "output_hashes": {},
                                "char_count": {},
                            }
                        else:
                            if self.state_manager.state[subj][fname].get("p1") != "⏭️":
                                self.state_manager.state[subj][fname]["p1"] = "⏭️"
            self.state_manager._save_state()
        self.process_tasks(
            self._process_file,
            force=force,
            subject_filter=subject,
            file_filter=file_filter,
            single_mode=single_mode,
            resume_from=resume_from,
        )

    def _process_file(self, idx: int, task: dict, total: int):
        subj = task["subject"]
        fname = task["filename"]
        p2_dir = getattr(
            self,
            "_p2_dir",
            self.dirs.get("p2", os.path.join(self.base_dir, "output", "02_transcript_proofread")),
        )
        in_path = os.path.join(p2_dir, subj, fname)

        if not os.path.exists(in_path):
            self.log(f"⚠️ 找不到輸入檔: {in_path}", "warn")
            return

        if fname == "correction_log.md":
            self.log(f"⏭️ 忽略日誌檔: {fname}", "debug")
            self.state_manager.update_task(subj, fname, "p3", "✅")
            return

        prefix = fname.split("_")[0] if "_" in fname else os.path.splitext(fname)[0]
        ref_text, figure_list = self._get_reference_data(subj, prefix)

        p3_dir = self.dirs.get("p3", os.path.join(self.base_dir, "output", "03_doc_completeness"))
        out_path = os.path.join(p3_dir, subj, fname)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        with open(in_path, encoding="utf-8") as f:
            raw_text = f.read()

        if not ref_text and not figure_list:
            self.log(f"⏭️ [{subj}] {fname}: 無參考講義或圖表，略過 Completeness Check。")
            AtomicWriter.write_text(out_path, raw_text)
            out_hash = self.state_manager.get_file_hash(out_path)
            self.state_manager.update_task(subj, fname, "p3", "✅", output_hash=out_hash)
            return

        prompt_tpl = self.get_prompt("Phase 3: Document Completeness")

        config = self.get_config("phase3", subject_name=subj)
        model_name = config.get("model", "gemma4:e4b")
        chunk_size = int(config.get("chunk_size", 4000))
        options = config.get("options", {})

        chunks = smart_split(raw_text, chunk_size)
        full_corrected = []
        full_logs = []

        pbar, stop_tick, t = self.create_spinner(f"完整性檢查 ({fname})")

        for c_idx, chunk in enumerate(chunks):
            if self.check_system_health():
                break

            pdf_block = f"[講義 PDF 參考]：\n{ref_text}\n\n[圖表清單]：\n{figure_list}\n\n"
            prompt = f"{prompt_tpl}\n\n{pdf_block}[本段語音轉錄稿]：\n{chunk}"

            try:
                res = self.llm.generate(model=model_name, prompt=prompt, options=options)
                corrected = res
                expl = ""
                if "---" in res:
                    parts_res = res.split("---", 1)
                    corrected = parts_res[0].strip()
                    expl = parts_res[1].strip()

                full_corrected.append(corrected)
                if expl:
                    full_logs.append(expl)
            except Exception as e:
                self.log(f"❌ 片段 {c_idx + 1} 失敗: {e}", "error")
                full_corrected.append(chunk)

        self.finish_spinner(pbar, stop_tick, t)
        self.llm.unload_model(model_name, logger=self)

        final_doc = "\n".join(full_corrected)

        self.log("ℹ️  [Phase 3] 自動校對完成，已存入待審核佇列 (可在 Dashboard 檢視)。")

        AtomicWriter.write_text(out_path, final_doc)

        log_path = os.path.join(p3_dir, subj, "correction_log.md")
        log_content = (
            f"\n\n## {fname} (Completeness)\n" + "\n".join(full_logs)
            if full_logs
            else f"\n\n## {fname}\nNo omissions found."
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_content)

        out_hash = self.state_manager.get_file_hash(out_path)
        self.state_manager.update_task(subj, fname, "p3", "✅", output_hash=out_hash)
        self.log(f"✅ [{idx}/{total}] 完整性檢查完成：{fname}")

        # --- Per-file EventBus Handoff ---
        workspace_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        EventBus.publish(
            DomainEvent(
                name="PipelineCompleted",
                source_skill="proofreader",
                payload={"filepath": out_path, "subject": subj, "chain": []},
            )
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    parser.add_argument("--file", type=str)
    args = parser.parse_args()
    Phase3DocCompleteness().run(force=args.force, subject=args.subject, file_filter=args.file)
