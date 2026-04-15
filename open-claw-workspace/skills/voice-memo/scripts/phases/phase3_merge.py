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

class Phase3Merge(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p3", phase_name="對話合併編排", logger=None)
        threshold = self.config_manager.get_nested("thresholds", "phase3_verbatim")
        if threshold is None:
            raise RuntimeError("voice-memo thresholds.phase3_verbatim is missing")
        self.P3_VERBATIM_THRESHOLD = float(threshold)
        lookback = self.config_manager.get_nested("context", "phase3_lookback_chars")
        if lookback is None:
            raise RuntimeError("voice-memo context.phase3_lookback_chars is missing")
        self.LOOKBACK_P3 = int(lookback)
        
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

    def _get_glossary(self, subject: str) -> str:
        import json
        gpath = os.path.join(self.dirs["p0"], subject, "glossary.json")
        if not os.path.exists(gpath): return ""
        try:
            with open(gpath, "r", encoding="utf-8") as f: gloss = json.load(f)
            if not gloss: return ""
            lines = [f"  「{k}」→「{v}」" for k, v in gloss.items()]
            return "【術語詞庫 — Whisper 聽寫修正對照表】：\n" + "\n".join(lines)
        except Exception: return ""

    def run(self, force=False, subject=None, resume_from=None):
        self.log(f"🧠 啟動 Phase 3：合併與對話編排模式")
        prompt_tpl = self.get_prompt("Phase 3: 合併與分段指令")
        
        tasks = self.get_tasks(prev_phase_key="p2", force=force, subject_filter=subject, resume_from=resume_from)
        if not tasks:
            self.log("📋 Phase 3 沒有待處理的檔案。")
            return
            
        groups = self._group_tasks(tasks)
        self.log(f"📋 共有 {len(tasks)} 個檔案，歸屬於 {len(groups)} 個合併群組。")
        models_used = set()
        
        idx = 1
        for (subj, base_name), tasks_in_group in groups.items():
            if self.check_system_health(): break
            
            config = self.get_config("phase3", subject_name=subj)
            model_name = config.get("model")
            chunk_size = int(config.get("chunk_size"))
            if not model_name:
                raise RuntimeError(f"phase3 config missing model for {subj}")
            if chunk_size <= 0:
                raise RuntimeError(f"phase3 config chunk_size must be > 0 for {subj}")
            options = config.get("options", {})
            models_used.add(model_name)
            
            self.log(f"📦 [{idx}/{len(groups)}] 正在合併並編排：[{subj}] {base_name}")
            idx += 1
            
            merged_parts = []
            for task in tasks_in_group:
                fname = task["filename"]
                proof_path = os.path.join(self.dirs["p2"], subj, f"{os.path.splitext(fname)[0]}.md")
                if os.path.exists(proof_path):
                    with open(proof_path, "r", encoding="utf-8") as f:
                        c = f.read()
                        if "## 📋 彙整修改日誌" in c:
                            clean, _ = c.split("## 📋 彙整修改日誌", 1)
                            merged_parts.append(clean.strip())
                        else:
                            merged_parts.append(c.strip())
                else:
                    self.log(f"⚠️ 找不到校對檔：{proof_path}", "warn")
                    
            if not merged_parts: continue
            
            full_text = "\n\n".join(merged_parts)
            gloss_block = self._get_glossary(subj)
            if gloss_block: gloss_block += "\n\n"
            
            chunks = self.smart_split(full_text, chunk_size)
            formatted = []
            p3_logs = []
            
            pbar, stop_tick, t = self.create_spinner(f"編排 ({base_name})")
            for c_idx, chunk in enumerate(chunks):
                if self.check_system_health(): break
                
                ctx_hint = ""
                if c_idx > 0 and formatted:
                    prev = formatted[-1]
                    ptail = prev[-self.LOOKBACK_P3:] if len(prev) > self.LOOKBACK_P3 else prev
                    ctx_hint = f"「前段結尾上下文（僅供參考，請勿在輸出中重複）」:\n...{ptail}\n\n"
                    
                prompt = f"{prompt_tpl}\n\n{gloss_block}《科目》: {subj}\n\n{ctx_hint}《待整理逸字稿》:\n{chunk}"
                
                try:
                    res = self.llm.generate(model=model_name, prompt=prompt, options=options)
                    res_stripped = res.strip()
                    
                    header = "## 📋 Phase 3 修改日誌"
                    body, raw_log = res_stripped, ""
                    if "---" in res_stripped and header in res_stripped:
                        b, a = res_stripped.split("---", 1)
                        body, raw_log = b.strip(), a.strip()
                        if raw_log.startswith(header): raw_log = raw_log[len(header):].strip()
                        
                        seen = None
                        dedup = []
                        for line in raw_log.splitlines():
                            s = line.strip()
                            if s == seen: continue
                            seen = s
                            dedup.append(line)
                        raw_log = "\n".join(dedup).strip()
                        
                    if len(body) < len(chunk) * self.P3_VERBATIM_THRESHOLD:
                        self.log(f"⚠️ 片段 {c_idx+1} [Phase 3 逐字稿守衛]: 輸出過短，回退至原文", "warn")
                        body = chunk
                        
                    formatted.append(body)
                    if raw_log: p3_logs.append(raw_log)
                        
                except Exception as e:
                    self.log(f"❌ 片段 {c_idx+1} 編排失敗: {e}", "error")
                    formatted.append(chunk)

            self.finish_spinner(pbar, stop_tick, t)
            
            final_doc = "\n\n".join(formatted)
            if p3_logs:
                final_doc += f"\n\n---\n\n## 📋 Phase 3 修改日誌\n\n" + "\n\n".join(p3_logs)
                
            out_path = os.path.join(self.dirs["p3"], subj, f"{base_name}.md")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(final_doc)
                
            out_hash = self.state_manager.get_file_hash(out_path)
            for task in tasks_in_group:
                self.state_manager.update_task(subj, task["filename"], "p3", status="✅", 
                                               char_count=len(final_doc), output_hash=out_hash)
            self.log(f"✅ 合併編排完成：{base_name}.md")

            # 暫停機制：每個群組完成後檢查是否要 checkpoint
            if self.stop_requested:
                remaining_groups = list(groups.items())[idx - 1:]  # idx 已遞增，此時指向下一個群組
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
    Phase3Merge().run(force=args.force, subject=args.subject)
