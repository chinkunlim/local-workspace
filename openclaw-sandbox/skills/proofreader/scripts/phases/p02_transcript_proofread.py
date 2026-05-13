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


class Phase2TranscriptProofread(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="p2", phase_name="Transcript Proofread", skill_name="proofreader"
        )
        self.LOOKBACK_CHARS = 200
        self.VERBATIM_THRESHOLD = 0.85

    def _workspace_root(self) -> str:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

    def _get_manifest_status(self, subject: str, prefix: str) -> str:
        """Determine reference mode for this transcript.

        1. session_manifest.json (written by inbox_daemon) — authoritative
        2. GlobalRegistry (written by doc_parser on completion) — daemon-free fallback
        3. semantic_only — no docs found anywhere
        """
        manifest_path = os.path.join(
            self._workspace_root(), "data", "raw", subject, ".session_manifest.json"
        )

        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    manifest = json.load(f)
                doc_files = manifest.get("doc_files", {})
                has_docs = False
                all_done = True
                for d_file, d_data in doc_files.items():
                    if d_file.startswith(prefix + "_"):
                        has_docs = True
                        if d_data.get("status") != "done":
                            all_done = False
                if has_docs:
                    return "with_reference" if all_done else "wait"
            except Exception:
                pass

        # Fallback: GlobalRegistry (written by doc_parser on completion)
        registry = GlobalRegistry(self._workspace_root())
        if registry.get_asset_paths(subject, prefix, "doc_parser"):
            return "with_reference"
        return "semantic_only"

    def _get_reference_data(self, subject: str, prefix: str) -> tuple[str, str]:
        """Fetch doc_parser reference text and figure list for this prefix."""
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
        self.log("🧠 啟動 Phase 2：Transcript Proofread")

        workspace_root = self._workspace_root()
        self._audio_dir = os.path.join(
            workspace_root, "data", "audio_transcriber", "output", "03_merged"
        )
        self.state_manager.raw_dir = self._audio_dir

        with self.state_manager._lock:
            if os.path.exists(self._audio_dir):
                subjects = (
                    [subject]
                    if subject
                    else [
                        d
                        for d in os.listdir(self._audio_dir)
                        if os.path.isdir(os.path.join(self._audio_dir, d))
                    ]
                )
                for subj in subjects:
                    subj_dir = os.path.join(self._audio_dir, subj)
                    if not os.path.isdir(subj_dir):
                        continue
                    if subj not in self.state_manager.state:
                        self.state_manager.state[subj] = {}
                    for fname in os.listdir(subj_dir):
                        if not fname.endswith(".md"):
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
        audio_dir = getattr(
            self, "_audio_dir", self._workspace_root() + "/data/audio_transcriber/output/03_merged"
        )
        in_path = os.path.join(audio_dir, subj, fname)

        if not os.path.exists(in_path):
            self.log(f"⚠️ 找不到輸入檔: {in_path}", "warn")
            return

        prefix = fname.split("_")[0] if "_" in fname else os.path.splitext(fname)[0]
        ref_text, _ = self._get_reference_data(subj, prefix)

        with open(in_path, encoding="utf-8") as f:
            raw_text = f.read()

        prompt_tpl = self.get_prompt("Phase 2: Transcript Proofread")

        config = self.get_config("phase2", subject_name=subj)
        model_name = config.get("model", "gemma4:e4b")
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

        self.log("ℹ️  [Phase 2] 自動校對完成，已存入待審核佇列 (可在 Dashboard 檢視)。")

        p2_dir = self.dirs.get(
            "p2", os.path.join(self.base_dir, "output", "02_transcript_proofread")
        )
        out_path = os.path.join(p2_dir, subj, fname)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        AtomicWriter.write_text(out_path, final_doc)

        log_path = os.path.join(p2_dir, subj, "correction_log.md")
        log_content = (
            f"\n\n## {fname}\n" + "\n".join(full_logs)
            if full_logs
            else f"\n\n## {fname}\nNo major corrections."
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_content)

        out_hash = self.state_manager.get_file_hash(out_path)
        self.state_manager.update_task(subj, fname, "p2", "✅", output_hash=out_hash)

        from core.orchestration.session_manifest import update_session_manifest

        orig_filename = fname.replace(".md", ".m4a")  # Approximation
        update_session_manifest(
            self._workspace_root(), subj, orig_filename, "proofreader", "done", "proofread_done"
        )

        self.log(f"✅ [{idx}/{total}] 校對完成：{fname}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    parser.add_argument("--file", type=str)
    args = parser.parse_args()
    Phase2TranscriptProofread().run(force=args.force, subject=args.subject, file_filter=args.file)
