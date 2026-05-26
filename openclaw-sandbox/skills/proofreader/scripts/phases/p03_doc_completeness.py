"""
Phase 2: Document Completeness
Compares proofread transcript against doc_parser reference, embeds images, and flags missing concepts.
"""

import json
import os
import sys

from phases.base_proofread import BaseProofreadPhase

# Internal Core Bootstrap
from core import AtomicWriter
from core.state.global_registry import GlobalRegistry
from core.utils.text_utils import smart_split


class Phase3DocCompleteness(BaseProofreadPhase):
    def __init__(self):
        super().__init__(phase_key="p3", phase_name="Doc Completeness", skill_name="proofreader")

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.log("🧠 啟動 Phase 3：Doc Completeness")

        self._p2_dir = self.dirs.get(
            "p2", os.path.join(self.base_dir, "output", "02_transcript_proofread")
        )
        self.process_tasks(
            self._process_file,
            force=force,
            subject_filter=subject,
            file_filter=file_filter,
            single_mode=single_mode,
            resume_from=resume_from,
        )

        self._unload_used_models()

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

        with open(in_path, encoding="utf-8") as f:
            raw_text = f.read()

        prefix = fname.split("_")[0] if "_" in fname else os.path.splitext(fname)[0]
        ref_text, figure_list = self._get_reference_data(
            subj, prefix, transcript_text=raw_text, use_semantic_fallback=True
        )

        p3_dir = self.dirs.get("p3", os.path.join(self.base_dir, "output", "03_doc_completeness"))
        out_path = os.path.join(p3_dir, subj, fname)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

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

        if not hasattr(self, "_used_models"):
            self._used_models = set()
        self._used_models.add(model_name)

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

        note_tag = (
            f"📚 參考: {', '.join(getattr(self, '_current_ref_files', []))}"
            if getattr(self, "_current_ref_files", [])
            else "無參考講義"
        )
        self.state_manager.update_task(
            subj, fname, "p3", "✅", output_hash=out_hash, note_tag=note_tag
        )
        self.log(f"✅ [{idx}/{total}] 完整性檢查完成：{fname}")

        # --- Per-file EventBus Handoff ---
        self.emit_completed(out_path, subj)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    parser.add_argument("--file", type=str)
    args = parser.parse_args()
    Phase3DocCompleteness().run(force=args.force, subject=args.subject, file_filter=args.file)
