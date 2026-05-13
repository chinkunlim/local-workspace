"""
Phase 0: Document Proofread
Reads raw_extracted.md and figure_list.md from doc_parser.
Proofreads the extracted text for completeness and embeds images in their correct logical positions.
"""

import json
import os
import sys

# Internal Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import AtomicWriter, PipelineBase
from core.utils.text_utils import smart_split


class Phase1DocProofread(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p1", phase_name="Doc Proofread", skill_name="proofreader")

    def _workspace_root(self) -> str:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.log("🧠 啟動 Phase 1：Doc Proofread")

        workspace_root = self._workspace_root()
        doc_input_dir = os.path.join(workspace_root, "data", "doc_parser", "output", "01_processed")

        # Manually scan 3-level doc_parser structure and inject into state_manager.state
        # Structure: 01_processed/{subject}/{pdf_id}/{pdf_id}_raw_extracted.md
        with self.state_manager._lock:
            subjects = (
                [subject]
                if subject
                else (
                    [
                        d
                        for d in os.listdir(doc_input_dir)
                        if os.path.isdir(os.path.join(doc_input_dir, d))
                    ]
                    if os.path.exists(doc_input_dir)
                    else []
                )
            )

            for subj in subjects:
                subj_dir = os.path.join(doc_input_dir, subj)
                if not os.path.isdir(subj_dir):
                    continue

                if subj not in self.state_manager.state:
                    self.state_manager.state[subj] = {}

                for pdf_id in os.listdir(subj_dir):
                    pdf_dir = os.path.join(subj_dir, pdf_id)
                    if not os.path.isdir(pdf_dir):
                        continue

                    # The "filename" key we'll use in state is pdf_id.md
                    fname = f"{pdf_id}.md"

                    if file_filter and fname != file_filter and pdf_id != file_filter:
                        continue

                    raw_md = os.path.join(pdf_dir, f"{pdf_id}_raw_extracted.md")
                    sanitized_md = os.path.join(pdf_dir, "sanitized.md")
                    if not os.path.exists(raw_md) and not os.path.exists(sanitized_md):
                        continue

                    if fname not in self.state_manager.state[subj]:
                        self.state_manager.state[subj][fname] = {
                            **dict.fromkeys(self.state_manager.PHASES, "⏳"),
                            "p2": "⏭️",
                            "p3": "⏭️",  # Doc files skip P2 and P3
                            "hash": "",
                            "date": "",
                            "note": "",
                            "output_hashes": {},
                            "char_count": {},
                        }
                    else:
                        if self.state_manager.state[subj][fname].get("p2") != "⏭️":
                            self.state_manager.state[subj][fname]["p2"] = "⏭️"
                        if self.state_manager.state[subj][fname].get("p3") != "⏭️":
                            self.state_manager.state[subj][fname]["p3"] = "⏭️"

            # Persist so get_tasks() can find these entries
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
        md_name = task["filename"]
        pdf_id = md_name.replace(".md", "")

        prompt_tpl = self.get_prompt("Phase 1: Document Proofread")
        if not prompt_tpl:
            prompt_tpl = (
                "You are an expert technical editor. Your task is to proofread the extracted markdown text from a document.\n"
                "1. Fix any OCR errors, broken sentences, or missing paragraphs to ensure it reads cohesively.\n"
                "2. The text may have missing images. A list of available figures (images) and their VLM descriptions is provided. "
                "You MUST embed these images `![caption](path)` at the exact appropriate location in the text where they contextually belong.\n"
                "3. Output ONLY the finalized markdown text. Do not output anything else."
            )

        workspace_root = self._workspace_root()
        doc_input_dir = os.path.join(workspace_root, "data", "doc_parser", "output", "01_processed")

        pdf_dir = os.path.join(doc_input_dir, subj, pdf_id)
        if not os.path.isdir(pdf_dir):
            self.log(f"⚠️ 找不到目錄: {pdf_dir}", "warn")
            return

        raw_md_path = os.path.join(pdf_dir, f"{pdf_id}_raw_extracted.md")
        sanitized_md_path = os.path.join(pdf_dir, "sanitized.md")
        in_path = sanitized_md_path if os.path.exists(sanitized_md_path) else raw_md_path

        if not os.path.exists(in_path):
            self.log(f"⚠️ 找不到輸入檔: {in_path}", "warn")
            return

        figure_list_path = os.path.join(pdf_dir, "figure_list.md")
        figure_list_content = ""
        if os.path.exists(figure_list_path):
            with open(figure_list_path, encoding="utf-8") as f:
                figure_list_content = f.read()

        with open(in_path, encoding="utf-8") as f:
            raw_text = f.read()

        config = self.get_config("phase1", subject_name=subj)
        model_name = config.get("model", "gemma4:e4b")
        chunk_size = int(config.get("chunk_size", 4000))
        options = config.get("options", {})

        chunks = smart_split(raw_text, chunk_size)
        full_corrected = []

        pbar, stop_tick, t = self.create_spinner(f"文件校對 ({pdf_id})")

        for c_idx, chunk in enumerate(chunks):
            if self.check_system_health():
                break

            fig_block = (
                f"[可用圖表清單]：\n{figure_list_content}\n\n" if figure_list_content else ""
            )
            prompt = f"{prompt_tpl}\n\n{fig_block}[本段文件原文]：\n{chunk}"

            try:
                res = self.llm.generate(model=model_name, prompt=prompt, options=options)
                full_corrected.append(res)
            except Exception as e:
                self.log(f"❌ 片段 {c_idx + 1} 失敗: {e}", "error")
                full_corrected.append(chunk)

        self.finish_spinner(pbar, stop_tick, t)
        self.llm.unload_model(model_name, logger=self)

        final_doc = "\n".join(full_corrected)

        self.log("ℹ️  [Phase 1] 自動校對完成，已存入待審核佇列 (可在 Dashboard 檢視)。")

        p1_dir = self.dirs.get("p1", os.path.join(self.base_dir, "output", "01_doc_proofread"))
        out_path = os.path.join(p1_dir, subj, f"{pdf_id}_proofread.md")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        AtomicWriter.write_text(out_path, final_doc)

        out_hash = self.state_manager.get_file_hash(out_path)
        self.state_manager.update_task(subj, md_name, "p1", "✅", output_hash=out_hash)

        from core.orchestration.session_manifest import update_session_manifest

        manifest_path = os.path.join(workspace_root, "data", "raw", subj, ".session_manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
                doc_files = manifest.get("doc_files", {})
                for d_file in doc_files:
                    if d_file.startswith(pdf_id):
                        update_session_manifest(
                            workspace_root,
                            subj,
                            d_file,
                            "proofreader",
                            "done",
                            "proofread_done",
                        )
                        break

        self.log(f"✅ [{idx}/{total}] 文件校對完成：{pdf_id}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    parser.add_argument("--file", type=str)
    args = parser.parse_args()
    Phase1DocProofread().run(force=args.force, subject=args.subject, file_filter=args.file)
