import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import PipelineBase


class Phase1ExtractKeyframes(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p1", phase_name="影片關鍵影格擷取", skill_name="video_ingester")
        ingest_cfg = self.config_manager.get_section("ingestion") or {}
        self.interval = ingest_cfg.get("keyframe_interval_sec", 30)
        self.resolution = ingest_cfg.get("resolution", "1280x720")

    def _process_file(self, idx: int, task: dict, total: int):
        subj = task["subject"]
        fname = task["filename"]

        in_path = os.path.join(self.base_dir, "input", subj, fname)
        if not os.path.exists(in_path):
            self.warning(f"⚠️ 找不到來源：{in_path}")
            return

        # We only process video files
        ext = os.path.splitext(fname)[1].lower()
        if ext not in [".mp4", ".mov", ".mkv", ".webm"]:
            self.warning(f"⚠️ 略過非影片檔案: {fname}")
            return

        stem = os.path.splitext(fname)[0]
        out_dir = os.path.join(self.base_dir, "output", "01_keyframes", subj, stem)
        os.makedirs(out_dir, exist_ok=True)

        # Check if already extracted
        existing = [f for f in os.listdir(out_dir) if f.endswith(".jpg")]
        if existing:
            self.info(f"✅ [{idx}/{total}] 已擷取過關鍵影格：{subj}/{stem} ({len(existing)} 影格)")
            self.state_manager.update_task(subj, fname, self.phase_key)
            return

        self.info(f"🎬 [{idx}/{total}] 擷取關鍵影格：[{subj}] {fname} (每 {self.interval} 秒)")

        # FFmpeg command: extract 1 frame every interval seconds
        # -vf fps=1/30: extract one frame per 30 seconds
        # -s 1280x720: scale
        out_pattern = os.path.join(out_dir, "frame_%04d.jpg")
        cmd = [
            "ffmpeg",
            "-i",
            in_path,
            "-vf",
            f"fps=1/{self.interval},scale={self.resolution}",
            "-q:v",
            "2",  # high quality JPEG
            out_pattern,
            "-y",  # overwrite
        ]

        try:
            # Run ffmpeg synchronously
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            extracted = len([f for f in os.listdir(out_dir) if f.endswith(".jpg")])
            self.info(f"✅ [{idx}/{total}] 擷取完成，共 {extracted} 幀。")
            self.state_manager.update_task(subj, fname, self.phase_key)
        except subprocess.CalledProcessError as e:
            self.error(f"❌ FFmpeg 執行失敗 {fname}: {e}")

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.info("✨ 啟動 Phase 1：影片關鍵影格擷取")
        self.process_tasks(
            self._process_file,
            force=force,
            subject_filter=subject,
            file_filter=file_filter,
            single_mode=single_mode,
            resume_from=resume_from,
        )
