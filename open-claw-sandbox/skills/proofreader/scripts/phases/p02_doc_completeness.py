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
from core.utils.text_utils import smart_split


class Phase2DocCompleteness(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p2", phase_name="Doc Completeness", skill_name="proofreader")

    def _get_reference_data(self, subject: str, prefix: str) -> tuple[str, str]:
        workspace_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        doc_processed_dir = os.path.join(
            workspace_root, "data", "doc_parser", "output", "01_processed", subject
        )

        if not os.path.exists(doc_processed_dir):
            return "", ""

        ref_text = ""
        figure_list_text = ""

        for item in os.listdir(doc_processed_dir):
            if item.startswith(prefix + "_"):
                cand_dir = os.path.join(doc_processed_dir, item)
                if os.path.isdir(cand_dir):
                    target_md = os.path.join(cand_dir, "sanitized.md")
                    if not os.path.exists(target_md):
                        target_md = os.path.join(cand_dir, f"{item}_raw_extracted.md")

                    if os.path.exists(target_md):
                        try:
                            with open(target_md, encoding="utf-8") as f:
                                ref_text += f.read()[:20000] + "\n\n"
                        except Exception:
                            pass

                    fig_list_path = os.path.join(cand_dir, "figure_list.md")
                    if os.path.exists(fig_list_path):
                        try:
                            with open(fig_list_path, encoding="utf-8") as f:
                                figure_list_text += f.read() + "\n\n"
                        except Exception:
                            pass

        return ref_text, figure_list_text

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.log("🧠 啟動 Phase 2：Doc Completeness")
        prompt_tpl = self.get_prompt("Phase 2: Document Completeness")

        p1_dir = self.dirs["p1"]

        subjects = [subject] if subject else (os.listdir(p1_dir) if os.path.exists(p1_dir) else [])

        for subj in subjects:
            subj_dir = os.path.join(p1_dir, subj)
            if not os.path.isdir(subj_dir):
                continue

            for fname in os.listdir(subj_dir):
                if not fname.endswith(".md") or fname == "correction_log.md":
                    continue

                if file_filter and fname != file_filter:
                    continue

                prefix = fname.split("_")[0] if "_" in fname else os.path.splitext(fname)[0]

                ref_text, figure_list = self._get_reference_data(subj, prefix)

                if not ref_text and not figure_list:
                    self.log(f"⏭️ [{subj}] {fname}: 無參考講義或圖表，略過 Completeness Check。")

                    # Copy to p2 directly
                    in_path = os.path.join(subj_dir, fname)
                    with open(in_path, encoding="utf-8") as f:
                        raw_text = f.read()
                    out_path = os.path.join(self.dirs["p2"], subj, fname)
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    AtomicWriter.write_text(out_path, raw_text)
                    continue

                in_path = os.path.join(subj_dir, fname)
                with open(in_path, encoding="utf-8") as f:
                    raw_text = f.read()

                config = self.get_config("phase2", subject_name=subj)
                model_name = config.get("model")
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

                # --- HITL Verification Gate (Removed) ---
                # Verification is now handled asynchronously via the centralized Dashboard.
                self.log("ℹ️  [Phase 2] 自動校對完成，已存入待審核佇列 (可在 Dashboard 檢視)。")

                # Write to output/02_doc_completeness
                out_path = os.path.join(self.dirs["p2"], subj, fname)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                AtomicWriter.write_text(out_path, final_doc)

                # Append to correction_log.md
                log_path = os.path.join(self.dirs["p2"], subj, "correction_log.md")
                log_content = (
                    f"\n\n## {fname} (Completeness)\n" + "\n".join(full_logs)
                    if full_logs
                    else f"\n\n## {fname}\nNo omissions found."
                )
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(log_content)

                self.log(f"✅ 完整性檢查完成：{fname}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    parser.add_argument("--file", type=str)
    args = parser.parse_args()
    Phase2DocCompleteness().run(force=args.force, subject=args.subject, file_filter=args.file)
