import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

import mlx_whisper

from core import AtomicWriter, PipelineBase


class Phase2TranscribeVideo(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="p2", phase_name="影片語音轉錄與圖文整合", skill_name="video_ingester"
        )
        self.prev_phase = "p1"
        self.model_name = (
            self.config_manager.get_nested("models", "whisper")
            or "mlx-community/whisper-large-v3-turbo"
        )

        ingest_cfg = self.config_manager.get_section("ingestion") or {}
        self.interval = ingest_cfg.get("keyframe_interval_sec", 30)

    def _process_file(self, idx: int, task: dict, total: int):
        subj = task["subject"]
        fname = task["filename"]
        stem = os.path.splitext(fname)[0]

        in_path = os.path.join(self.base_dir, "input", subj, fname)
        if not os.path.exists(in_path):
            self.warning(f"⚠️ 找不到來源：{in_path}")
            return

        ext = os.path.splitext(fname)[1].lower()
        if ext not in [".mp4", ".mov", ".mkv", ".webm"]:
            return

        keyframes_dir = os.path.join(self.base_dir, "output", "01_keyframes", subj, stem)
        if not os.path.exists(keyframes_dir):
            self.warning(f"⚠️ 找不到關鍵影格目錄：{keyframes_dir}")
            return

        out_dir = os.path.join(self.base_dir, "output", "02_transcription", subj)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{stem}.md")

        self.info(f"🎙️ [{idx}/{total}] 語音轉錄中：[{subj}] {fname} using {self.model_name}...")

        try:
            # We use mlx-whisper with word-level timestamps to match with keyframes
            res = mlx_whisper.transcribe(
                in_path, path_or_hf_repo=self.model_name, word_timestamps=True
            )

            # Group transcription into blocks corresponding to keyframes
            # Every `self.interval` seconds, we insert the keyframe image
            blocks = []
            current_block_text: list[str] = []
            current_frame_idx = 1

            # Get all frames, sorted
            frames = sorted([f for f in os.listdir(keyframes_dir) if f.endswith(".jpg")])

            for segment in res.get("segments", []):
                for word in segment.get("words", []):
                    start = word["start"]
                    text = word["word"]

                    # Determine which frame interval we are in
                    target_frame_idx = int(start // self.interval) + 1

                    if target_frame_idx > current_frame_idx:
                        # Close out current block
                        if current_block_text:
                            blocks.append((current_frame_idx, "".join(current_block_text).strip()))
                        current_block_text = [text]
                        current_frame_idx = target_frame_idx
                    else:
                        current_block_text.append(text)

            # Close the last block
            if current_block_text:
                blocks.append((current_frame_idx, "".join(current_block_text).strip()))

            # Construct final Markdown
            md_lines = [f"# {stem}", ""]
            for f_idx, text in blocks:
                frame_filename = f"frame_{f_idx:04d}.jpg"
                if frame_filename in frames:
                    # Construct absolute path for the image to be compatible with Obsidian/note generator
                    img_path = os.path.join(keyframes_dir, frame_filename)
                    md_lines.append(f"![[{frame_filename}]]({img_path})")
                    md_lines.append("")
                md_lines.append(text)
                md_lines.append("")

            AtomicWriter.write_text(out_path, "\n".join(md_lines))
            self.info(f"✅ [{idx}/{total}] 轉錄完成：{out_path}")
            self.state_manager.update_task(subj, fname, self.phase_key)

            # Send to note_generator if available
            note_gen_inbox = os.path.join(
                self.workspace_root, "skills", "note_generator", "data", "input", subj
            )
            os.makedirs(note_gen_inbox, exist_ok=True)
            import shutil

            shutil.copy2(out_path, os.path.join(note_gen_inbox, f"{stem}.md"))
            self.info(f"  ↪️ 已轉發至 note_generator: {subj}/{stem}.md")

        except Exception as e:
            self.error(f"❌ 轉錄失敗 {fname}: {e}")

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.info("✨ 啟動 Phase 2：影片語音轉錄與圖文整合")
        # Ensure Phase 1 state is loaded
        self.state_manager._load_state()

        self.process_tasks(
            self._process_file,
            prev_phase_key=self.prev_phase,
            force=force,
            subject_filter=subject,
            file_filter=file_filter,
            single_mode=single_mode,
            resume_from=resume_from,
        )
