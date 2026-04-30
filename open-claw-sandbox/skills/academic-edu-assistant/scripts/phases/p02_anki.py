import os
import sys

# Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import AtomicWriter, PipelineBase


class Phase2Anki(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="p2", phase_name="Anki 卡片生成", skill_name="academic-edu-assistant"
        )
        self.prev_phase = "p1"

    def _process_file(self, idx: int, task: dict, total: int):
        subj = task["subject"]
        fname = task["filename"]

        # In this Option B flow, the input for Phase 2 is the output of Phase 1
        in_path = os.path.join(self.base_dir, "output", "01_comparison", fname)
        if not os.path.exists(in_path):
            self.warning(f"⚠️ 找不到比較報告：{in_path}")
            return

        with open(in_path, encoding="utf-8") as f:
            content = f.read()

        prompt_tpl = self.get_prompt("Phase 2: Anki 卡片生成")
        if not prompt_tpl:
            self.error("❌ 找不到 prompt 指令，請確認 prompt.md 存在")
            return

        prompt = f"""{prompt_tpl}

【比較報告開始】
{content}
【比較報告結束】
"""
        model_name = self.config_manager.get_nested("models", "default") or "qwen2.5-coder:7b"
        pbar, stop_tick, t = self.create_spinner(f"生成 Anki 卡片 ({fname}) using {model_name}...")
        try:
            response = self.llm.generate(model=model_name, prompt=prompt)
        except Exception as e:
            self.error(f"❌ 生成失敗: {e}")
            return
        finally:
            self.finish_spinner(pbar, stop_tick, t)
            # C Fix: unload model after use to release VRAM
            self.llm.unload_model(model_name, logger=self)

        out_dir = os.path.join(self.base_dir, "output", "02_anki")
        os.makedirs(out_dir, exist_ok=True)

        out_path = os.path.join(out_dir, f"{os.path.splitext(fname)[0]}.csv")
        AtomicWriter.write_text(out_path, response.strip() + "\n")

        self.info(f"✅ Anki 卡片已匯出: {out_path}")
        self.state_manager.update_task(subj, fname, self.phase_key)

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.info("✨ 啟動 Phase 2：Anki 卡片生成")

        # Reload state because Phase 1 dynamically generated files and state
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
