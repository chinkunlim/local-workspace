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


class Phase0DocProofread(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p0", phase_name="Doc Proofread", skill_name="proofreader")

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.log("🧠 啟動 Phase 0：Doc Proofread")
        prompt_tpl = self.get_prompt("Phase 0: Document Proofread")

        # If no prompt exists, fallback to a sensible default
        if not prompt_tpl:
            prompt_tpl = (
                "You are an expert technical editor. Your task is to proofread the extracted markdown text from a document.\n"
                "1. Fix any OCR errors, broken sentences, or missing paragraphs to ensure it reads cohesively.\n"
                "2. The text may have missing images. A list of available figures (images) and their VLM descriptions is provided. "
                "You MUST embed these images `![caption](path)` at the exact appropriate location in the text where they contextually belong.\n"
                "3. Output ONLY the finalized markdown text. Do not output anything else."
            )

        workspace_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
        )
        doc_input_dir = os.path.join(workspace_root, "data", "doc_parser", "output", "01_processed")

        subjects = (
            [subject]
            if subject
            else (os.listdir(doc_input_dir) if os.path.exists(doc_input_dir) else [])
        )

        for subj in subjects:
            subj_dir = os.path.join(doc_input_dir, subj)
            if not os.path.isdir(subj_dir):
                continue

            for pdf_id in os.listdir(subj_dir):
                pdf_dir = os.path.join(subj_dir, pdf_id)
                if not os.path.isdir(pdf_dir):
                    continue

                if file_filter and pdf_id != file_filter and pdf_id + ".md" != file_filter:
                    continue

                raw_md_path = os.path.join(pdf_dir, f"{pdf_id}_raw_extracted.md")
                sanitized_md_path = os.path.join(pdf_dir, "sanitized.md")

                # Pick the best available text
                in_path = sanitized_md_path if os.path.exists(sanitized_md_path) else raw_md_path
                if not os.path.exists(in_path):
                    continue

                figure_list_path = os.path.join(pdf_dir, "figure_list.md")
                figure_list_content = ""
                if os.path.exists(figure_list_path):
                    with open(figure_list_path, encoding="utf-8") as f:
                        figure_list_content = f.read()

                with open(in_path, encoding="utf-8") as f:
                    raw_text = f.read()

                config = self.get_config("phase0", subject_name=subj)
                model_name = config.get("model", "qwen3:14b")
                chunk_size = int(config.get("chunk_size", 4000))
                options = config.get("options", {})

                chunks = smart_split(raw_text, chunk_size)
                full_corrected = []

                pbar, stop_tick, t = self.create_spinner(f"文件校對 ({pdf_id})")

                for c_idx, chunk in enumerate(chunks):
                    if self.check_system_health():
                        break

                    fig_block = (
                        f"[可用圖表清單]：\n{figure_list_content}\n\n"
                        if figure_list_content
                        else ""
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

                # --- HITL Verification Gate (Removed) ---
                # Verification is now handled asynchronously via the centralized Dashboard.
                self.log("ℹ️  [Phase 0] 自動校對完成，已存入待審核佇列 (可在 Dashboard 檢視)。")

                # Write to output/00_doc_proofread
                p0_dir = self.dirs.get(
                    "p0", os.path.join(self.base_dir, "output", "00_doc_proofread")
                )
                out_path = os.path.join(p0_dir, subj, f"{pdf_id}_proofread.md")
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                AtomicWriter.write_text(out_path, final_doc)

                # Update Manifest for this document to say proofread is done
                from core.orchestration.session_manifest import update_session_manifest

                # Try to map back to original extension
                manifest_path = os.path.join(
                    workspace_root, "data", "raw", subj, ".session_manifest.json"
                )
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

                self.log(f"✅ 文件校對完成：{pdf_id}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    parser.add_argument("--file", type=str)
    args = parser.parse_args()
    Phase0DocProofread().run(force=args.force, subject=args.subject, file_filter=args.file)
