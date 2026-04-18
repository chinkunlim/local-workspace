# -*- coding: utf-8 -*-
"""
Phase 0: Automatic Glossary Generation
Refactored to V7.0 OOP Architecture
"""

# Group 1 — stdlib
import os
import sys
import json
import glob

# Group 2 — Internal Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.bootstrap import ensure_core_path as _bootstrap
_bootstrap(__file__)

# Group 3 — Core imports
from core import PipelineBase

class Phase0Glossary(PipelineBase):
    def __init__(self):
        # We define phase_key as 'p0' for phase 0 context
        super().__init__(phase_key="p0", phase_name="詞庫自動生成", logger=None)
        self.prompt_tpl = self.get_prompt("Phase 0: 詞庫自動生成指令")
        
        self.SAMPLE_CHARS = 3000
        self.MAX_FILES = 3
        
    def _build_sample(self, subj: str) -> str:
        t_dir = self.dirs["p1"]
        if not os.path.exists(os.path.join(t_dir, subj)): return ""
        files = sorted([f for f in glob.glob(os.path.join(t_dir, subj, "*.md")) if "_timestamped" not in f])
        
        parts = []
        for f in files[:self.MAX_FILES]:
            with open(f, "r", encoding="utf-8") as file:
                parts.append(f"--- 【{os.path.basename(f)}】---\n{file.read(self.SAMPLE_CHARS)}")
        return "\n\n".join(parts)
        
    def _parse_json(self, response: str) -> dict:
        import re
        code_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if code_block:
            try: return json.loads(code_block.group(1))
            except json.JSONDecodeError: pass
            
        obj_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if obj_match:
            try: return json.loads(obj_match.group(0))
            except json.JSONDecodeError: pass
            
        try: return json.loads(response.strip())
        except json.JSONDecodeError: return {}

    def run(self, force=False, merge=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.log(f"📚 啟動 Phase 0：詞庫自動生成")
        if not self.prompt_tpl:
            self.log("❌ 找不到 Phase 0 的 prompt 指令，請確認 prompt.md 內有對應的段落。", "error")
            return
            
        raw_dir = self.dirs["p0"]
        if not os.path.isdir(raw_dir): 
            self.log("❌ 找不到 raw_data 目錄", "error")
            return
        
        all_subs = [d for d in os.listdir(raw_dir) if os.path.isdir(os.path.join(raw_dir, d))]
        target_subjects = [subject] if subject else None
        subs = [s for s in target_subjects if s in all_subs] if target_subjects else all_subs
        
        if not subs:
            self.log("📋 沒有需要處理的科目。")
            return
            
        self.log(f"📋 Phase 0 將處理 {len(subs)} 個科目：{subs}")
        models_used = set()
        
        for idx, subj in enumerate(subs, 1):
            if self.check_system_health(): break
            
            config = self.get_config("phase0", subject_name=subj)
            model_name = config.get("model")
            if not model_name:
                raise RuntimeError(f"phase0 config missing model for {subj}")
            options = config.get("options", {})
            models_used.add(model_name)
            
            out_path = os.path.join(raw_dir, subj, "glossary.json")
            existing = {}
            if os.path.exists(out_path):
                try:
                    with open(out_path, "r", encoding="utf-8") as f: existing = json.load(f)
                except Exception: pass
                
            if os.path.exists(out_path) and not force and not merge:
                self.log(f"⏭️  [{idx}/{len(subs)}] 已有詞庫，跳過：{subj} (可使用 --force 覆蓋, 或 --merge 合併)")
                continue
                
            sample = self._build_sample(subj)
            if not sample: 
                self.log(f"⚠️  [{idx}/{len(subs)}] 找不到 {subj} 的逐字稿，跳過。", "warn")
                continue
            
            prompt = f"{self.prompt_tpl}\n\n【科目名稱】: {subj}\n\n【逐字稿樣本】:\n{sample}"
            self.log(f"🧠 [{idx}/{len(subs)}] 正在分析誤聽詞 ({model_name})：{subj}...")
            
            pbar, stop_tick, t = self.create_spinner(f"生成 ({subj})")
            try:
                res = self.llm.generate(model=model_name, prompt=prompt, options=options, logger=self)
            except Exception as e:
                self.log(f"❌ LLM 失敗 ({subj}): {e}", "error")
                continue
            finally:
                self.finish_spinner(pbar, stop_tick, t)
                
            suggested = self._parse_json(res)
            suggested = {k: v for k, v in suggested.items() if k.strip() != v.strip()}
            
            if merge and existing:
                merged = dict(existing)
                added = 0
                for k, v in suggested.items(): 
                    if k not in merged:
                        merged[k] = v
                        added += 1
                final_gloss = merged
                self.log(f"   合併模式：加入 {added} 筆新條目 (保留 {len(existing)} 筆現有)")
            else:
                final_gloss = suggested
                
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(final_gloss, f, ensure_ascii=False, indent=2)
                self.log(f"✅ [{idx}/{len(subs)}] 詞庫已儲存：{subj}/glossary.json (共 {len(final_gloss)} 筆)")
            except Exception as e:
                self.log(f"❌ 寫入失敗: {e}", "error")
            
        for m in models_used:
            self.llm.unload_model(m, logger=self)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", "-s", type=str)
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--merge", "-m", action="store_true")
    args = parser.parse_args()
    if args.force and args.merge:
        print("❌ --force 和 --merge 不能同時使用，請擇一。")
        import sys; sys.exit(1)
    Phase0Glossary().run(force=args.force, merge=args.merge, subject=args.subject)
