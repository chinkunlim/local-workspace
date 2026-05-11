"""
Phase 1: Transcript Proofread
Reads transcript from audio_transcriber output, and reference docs from doc_parser output.
Checks session manifest to determine if we run in `with_reference` or `semantic_only` mode.
If reference docs are still pending, it aborts (waiting for doc_parser to trigger it later).
"""

import json
import os
import re
import sys

# Internal Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import AtomicWriter, PipelineBase
from core.state.global_registry import GlobalRegistry
from core.utils.text_utils import smart_split


class Phase1TranscriptProofread(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="p1", phase_name="Transcript Proofread", skill_name="proofreader"
        )
        self.LOOKBACK_CHARS = 200
        self.VERBATIM_THRESHOLD = 0.85

    def _get_manifest_status(self, subject: str, prefix: str) -> str:
        """
        Check session manifest to decide mode.
        Returns "wait" if docs are pending, "with_reference" if docs are done, "semantic_only" if no docs.
        """
        workspace_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        manifest_path = os.path.join(
            workspace_root, "data", "raw", subject, ".session_manifest.json"
        )

        if not os.path.exists(manifest_path):
            return "semantic_only"

        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            return "semantic_only"

        doc_files = manifest.get("doc_files", {})

        has_docs = False
        all_done = True

        for d_file, d_data in doc_files.items():
            if d_file.startswith(prefix + "_"):
                has_docs = True
                if d_data.get("status") != "done":
                    all_done = False

        if not has_docs:
            return "semantic_only"
        elif not all_done:
            return "wait"
        else:
            return "with_reference"

    def _get_reference_text(self, subject: str, prefix: str) -> str:
        workspace_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        registry = GlobalRegistry(workspace_root)
        assets = registry.get_assets(subject, prefix)

        ref_text = ""
        doc_path = assets.get("doc_parser")
        if doc_path and os.path.exists(doc_path):
            try:
                with open(doc_path, encoding="utf-8") as f:
                    ref_text = f.read()[:20000] + "\n\n"
            except Exception:
                pass
        return ref_text

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.log("🧠 啟動 Phase 1：Transcript Proofread")
        prompt_tpl = self.get_prompt("Phase 1: Transcript Proofread")

        # Audio input comes from audio_transcriber output (p03_merged or p02_glossary_apply if p3 is skipped)
        workspace_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        audio_output_dir = os.path.join(
            workspace_root, "data", "audio_transcriber", "output", "03_merged"
        )

        if subject:
            subjects = [subject]
        else:
            subjects = os.listdir(audio_output_dir) if os.path.exists(audio_output_dir) else []

        for subj in subjects:
            subj_dir = os.path.join(audio_output_dir, subj)
            if not os.path.isdir(subj_dir):
                continue

            for fname in os.listdir(subj_dir):
                if not fname.endswith(".md"):
                    continue

                if file_filter and fname != file_filter:
                    continue

                prefix = fname.split("_")[0] if "_" in fname else os.path.splitext(fname)[0]

                status = self._get_manifest_status(subj, prefix)
                if status == "wait" and not force:
                    self.log(f"⏳ [{subj}] {fname}: 相關講義尚未解析完成，等待中...")
                    continue

                in_path = os.path.join(subj_dir, fname)
                with open(in_path, encoding="utf-8") as f:
                    raw_text = f.read()

                ref_text = ""
                if status == "with_reference":
                    ref_text = self._get_reference_text(subj, prefix)
                    self.log(f"📚 [{subj}] {fname}: 使用講義參考模式 (Reference mode)")
                else:
                    self.log(f"📝 [{subj}] {fname}: 純語義校對模式 (Semantic only mode)")

                config = self.get_config("phase1", subject_name=subj)
                model_name = config.get("model")
                chunk_size = int(config.get("chunk_size", 3000))
                options = config.get("options", {})

                chunks = smart_split(raw_text, chunk_size)
                full_corrected = []
                full_logs = []

                pbar, stop_tick, t = self.create_spinner(f"校對 ({fname})")

                for c_idx, chunk in enumerate(chunks):
                    if self.check_system_health():
                        break

                    context_hint = ""
                    if c_idx > 0:
                        prev_tail = raw_text[
                            max(0, c_idx * chunk_size - self.LOOKBACK_CHARS) : c_idx * chunk_size
                        ]
                        context_hint = (
                            f"[前段結尾上下文（僅供參考，請勿在輸出中重複）]：\n...{prev_tail}\n\n"
                        )

                    pdf_block = f"[講義 PDF 參考]：\n{ref_text}\n\n" if ref_text else ""
                    prompt = f"{prompt_tpl}\n\n{pdf_block}{context_hint}[本段逐字稿原文]：\n{chunk}"

                    try:
                        res = self.llm.generate(model=model_name, prompt=prompt, options=options)
                        corrected = res
                        expl = ""
                        if "---" in res:
                            parts_res = res.split("---", 1)
                            corrected = parts_res[0].strip()
                            expl = parts_res[1].strip()

                        if len(corrected) < len(chunk) * self.VERBATIM_THRESHOLD:
                            self.log(f"⚠️ 片段 {c_idx + 1} 觸發守衛: 過短，保留原文", "warn")
                            full_corrected.append(chunk)
                        else:
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
                self.log("ℹ️  [Phase 1] 自動校對完成，已存入待審核佇列 (可在 Dashboard 檢視)。")

                # Write to output/01_transcript_proofread
                out_path = os.path.join(self.dirs["p1"], subj, fname)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                AtomicWriter.write_text(out_path, final_doc)

                # Append to correction_log.md
                log_path = os.path.join(self.dirs["p1"], subj, "correction_log.md")
                log_content = (
                    f"\n\n## {fname}\n" + "\n".join(full_logs)
                    if full_logs
                    else f"\n\n## {fname}\nNo major corrections."
                )
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(log_content)

                # Update Manifest
                from core.orchestration.session_manifest import update_session_manifest

                orig_filename = fname.replace(".md", ".m4a")  # Approximation
                update_session_manifest(
                    workspace_root, subj, orig_filename, "proofreader", "done", "proofread_done"
                )

                self.log(f"✅ 校對完成：{fname}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    parser.add_argument("--file", type=str)
    args = parser.parse_args()
    Phase1TranscriptProofread().run(force=args.force, subject=args.subject, file_filter=args.file)
