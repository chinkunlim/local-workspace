# -*- coding: utf-8 -*-
import sys, os

# --- Boundary-Safe Initialization ---
_phase_dir = os.path.dirname(os.path.abspath(__file__))
_scripts_dir = os.path.dirname(_phase_dir)
_skill_root = os.path.dirname(os.path.dirname(_scripts_dir))  # skills/voice-memo
_openclawed_root = os.path.dirname(_skill_root)  # open-claw-workspace
_core_dir = os.path.abspath(os.path.join(_openclawed_root, "core"))
_workspace_root = os.environ.get(
    "WORKSPACE_DIR",
    os.path.dirname(_openclawed_root)  # local-workspace
)

# Enforce sandbox boundary: only core and this skill
sys.path = [_core_dir, _scripts_dir]

import os
import re
from core import PipelineBase

class Phase4Highlight(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p4", phase_name="重點標記", logger=None)
        threshold = self.config_manager.get_nested("thresholds", "phase4_verbatim")
        if threshold is None:
            raise RuntimeError("voice-memo thresholds.phase4_verbatim is missing")
        self.VERBATIM_THRESHOLD = float(threshold)
        
    def _get_lecture_base(self, fname: str):
        stem = os.path.splitext(fname)[0]
        m = re.match(r'^(.+)-(\d+)$', stem)
        if m: return m.group(1), int(m.group(2))
        return stem, None

    def _group_tasks(self, tasks):
        groups = {}
        for task in tasks:
            base, _seg = self._get_lecture_base(task["filename"])
            key = (task["subject"], base)
            groups.setdefault(key, []).append(task)
        for key in groups:
            groups[key].sort(key=lambda t: self._get_lecture_base(t["filename"])[1] or 0)
        return groups

    def run(self, force=False, subject=None, resume_from=None):
        self.log(f"🧠 啟動 Phase 4：動態上色與重點標記模式 (Anti-Tampering)")
        prompt_tpl = self.get_prompt("Phase 4: 重點標記指令")
        
        tasks = self.get_tasks(prev_phase_key="p3", force=force, subject_filter=subject, resume_from=resume_from)
        if not tasks:
            self.log("📋 Phase 4 沒有待處理的檔案。")
            return
            
        groups = self._group_tasks(tasks)
        self.log(f"📋 共有 {len(tasks)} 個檔案，歸屬於 {len(groups)} 個標記群組。")
        models_used = set()
        
        idx = 1
        for (subj, base_name), tasks_in_group in groups.items():
            if self.check_system_health(): break
            
            config = self.get_config("phase4", subject_name=subj)
            model_name = config.get("model")
            chunk_size = int(config.get("chunk_size"))
            if not model_name:
                raise RuntimeError(f"phase4 config missing model for {subj}")
            if chunk_size <= 0:
                raise RuntimeError(f"phase4 config chunk_size must be > 0 for {subj}")
            options = config.get("options", {})
            models_used.add(model_name)
            
            self.log(f"📦 [{idx}/{len(groups)}] 正在標記：[{subj}] {base_name}.md")
            idx += 1
            
            source_path = os.path.join(self.dirs["p3"], subj, f"{base_name}.md")
            if not os.path.exists(source_path):
                self.log(f"⚠️ 找不到合併檔：{source_path}", "warn")
                continue
                
            with open(source_path, "r", encoding="utf-8") as f:
                full_text = f.read()

            p3_log_tail = ""
            if "## 📋 Phase 3 修改日誌" in full_text:
                body, p3_log_tail = full_text.split("## 📋 Phase 3 修改日誌", 1)
                full_text = body.rstrip().rstrip("-").strip()
                p3_log_tail = "## 📋 Phase 3 修改日誌" + p3_log_tail

            chunks = self.smart_split(full_text, chunk_size)
            highlighted_parts = []
            
            pbar, stop_tick, t = self.create_spinner(f"標記 ({base_name})")
            for c_idx, chunk in enumerate(chunks):
                if self.check_system_health(): break
                
                try:
                    prompt = f"{prompt_tpl}\n\n【Original Text to Highlight】:\n{chunk}"
                    res = self.llm.generate(model=model_name, prompt=prompt, options=options)
                    
                    if len(res) < len(chunk) * self.VERBATIM_THRESHOLD:
                        self.log(f"⚠️ 片段 {c_idx+1} [防竄改觸發]: LLM 刪減過多，還原原文", "warn")
                        highlighted_parts.append(chunk)
                    else:
                        highlighted_parts.append(res.strip())
                except Exception as e:
                    self.log(f"❌ 片段 {c_idx+1} 標記失敗: {e}", "error")
                    highlighted_parts.append(chunk)
            
            self.finish_spinner(pbar, stop_tick, t)
            
            final_doc = "\n\n".join(highlighted_parts)
            if p3_log_tail: final_doc += f"\n\n---\n\n{p3_log_tail}"
            
            out_path = os.path.join(self.dirs["p4"], subj, f"{base_name}.md")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(final_doc)
                
            out_hash = self.state_manager.get_file_hash(out_path)
            for task in tasks_in_group:
                self.state_manager.update_task(subj, task["filename"], "p4", status="✅", 
                                               char_count=len(final_doc), output_hash=out_hash)
            self.log(f"✅ 重點上色完成：{base_name}.md")

            # 暫停機制：每個群組完成後檢查是否要 checkpoint
            if self.stop_requested:
                remaining_groups = list(groups.items())[idx - 1:]  # idx 已遞增，指向下一個群組
                if self.pause_requested and remaining_groups:
                    (next_subj, next_base), next_tasks = remaining_groups[0]
                    self.save_checkpoint(next_tasks[0]["subject"], next_tasks[0]["filename"])
                break

        for m in models_used:
            self.llm.unload_model(m, logger=self)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    args = parser.parse_args()
    Phase4Highlight().run(force=args.force, subject=args.subject)
