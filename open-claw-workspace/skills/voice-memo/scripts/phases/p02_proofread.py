# -*- coding: utf-8 -*-
import sys, os

import os, sys
from core.bootstrap import ensure_core_path as _bootstrap
_bootstrap(__file__)
_workspace_root = os.environ.get("WORKSPACE_DIR", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../..")))

import os
import re
from pypdf import PdfReader
from core import PipelineBase

class Phase2Proofread(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p2", phase_name="上下文校對", logger=None)
        lookback = self.config_manager.get_nested("context", "phase2_lookback_chars")
        if lookback is None:
            raise RuntimeError("voice-memo context.phase2_lookback_chars is missing")
        self.LOOKBACK_CHARS = int(lookback)
        threshold = self.config_manager.get_nested("thresholds", "phase2_verbatim")
        if threshold is None:
            raise RuntimeError("voice-memo thresholds.phase2_verbatim is missing")
        self.VERBATIM_THRESHOLD = float(threshold)
        
    def _get_glossary(self, subject: str) -> str:
        import json
        glossary_path = os.path.join(self.dirs["p0"], subject, "glossary.json")
        if not os.path.exists(glossary_path): return ""
        try:
            with open(glossary_path, "r", encoding="utf-8") as f: gloss = json.load(f)
            if not gloss: return ""
            lines = [f"  「{k}」→「{v}」" for k, v in gloss.items()]
            self.log(f"📚 已載入詞庫 ({subject}/glossary.json，共 {len(gloss)} 筆)")
            return "【術語詞庫 — Whisper 聽寫修正對照表】：\n" + "\n".join(lines)
        except Exception as e:
            self.log(f"⚠️ 詞庫載入失敗: {e}", "warn")
            return ""

    def run(self, force=False, subject=None, resume_from=None):
        self.log(f"🧠 啟動 Phase 2：校對模式")
        prompt_tpl = self.get_prompt("Phase 2: 校對指令")
        
        tasks = self.get_tasks(prev_phase_key="p1", force=force, subject_filter=subject, resume_from=resume_from)
        
        if not tasks:
            self.log("📋 Phase 2 沒有待校對的檔案。")
            return
            
        self.log(f"📋 Phase 2 共有 {len(tasks)} 個檔案待校對。")
        models_used = set()
        
        for idx, task in enumerate(tasks, 1):
            if self.check_system_health(): break
            
            subj, fname = task["subject"], task["filename"]
            
            config = self.get_config("phase2", subject_name=subj)
            model_name = config.get("model")
            chunk_size = int(config.get("chunk_size"))
            if not model_name:
                raise RuntimeError(f"phase2 config missing model for {subj}")
            if chunk_size <= 0:
                raise RuntimeError(f"phase2 config chunk_size must be > 0 for {subj}")
            options = config.get("options", {})
            models_used.add(model_name)
            
            base_name = fname.replace(".m4a", "")
            
            # --- Load Extra Context ---
            glossary_text = self._get_glossary(subj)
            pdf_text = ""
            pdf_path = os.path.join(self.dirs["p0"], subj, f"{base_name}.pdf")
            
            if os.path.exists(pdf_path):
                try:
                    reader = PdfReader(pdf_path)
                    pdf_text = "\n".join([p.extract_text() for p in reader.pages[:20] if p.extract_text()])[:20000]
                    self.log(f"📖 已載入 PDF 參考 ({len(pdf_text)} 字元)")
                except Exception as e:
                    self.log(f"⚠️ PDF 讀取錯誤: {e}", "warn")
            else:
                m = re.match(r'^(.+)-(\d+)$', base_name)
                if m:
                    lecture_base = m.group(1)
                    shared_pdf = os.path.join(self.dirs["p0"], subj, f"{lecture_base}.pdf")
                    if os.path.exists(shared_pdf):
                        try:
                            reader = PdfReader(shared_pdf)
                            pdf_text = "\n".join([p.extract_text() for p in reader.pages[:20] if p.extract_text()])[:20000]
                            self.log(f"📖 已載入共用 PDF ({lecture_base}.pdf)")
                        except Exception: pass
            
            # --- Load P1 Transform ---
            in_path = os.path.join(self.dirs["p1"], subj, f"{base_name}.md")
            if not os.path.exists(in_path): 
                self.log(f"⚠️ 找不到 P1 來源: {in_path}", "warn")
                continue
                
            with open(in_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
                
            chunks = self.smart_split(raw_text, chunk_size)
            full_corrected = []
            full_logs = []
            
            self.log(f"📦 [{idx}/{len(tasks)}] 正在校對：[{subj}] {base_name}.md (共分為 {len(chunks)} 段)")
            
            pbar, stop_tick, t = self.create_spinner(f"校對 ({fname})")
            
            for c_idx, chunk in enumerate(chunks):
                if self.check_system_health(): break
                
                context_hint = ""
                if c_idx > 0:
                    prev_tail = raw_text[max(0, c_idx * chunk_size - self.LOOKBACK_CHARS):c_idx * chunk_size]
                    context_hint = f"【前段結尾上下文（僅供參考，請勿在輸出中重複此段）】：\n...{prev_tail}\n\n"
                    
                pdf_block = f"【講義 PDF 參考】：\n{pdf_text}\n\n" if pdf_text else ""
                gloss_block = f"{glossary_text}\n\n" if glossary_text else ""
                
                full_prompt = f"{prompt_tpl}\n\n{gloss_block}{pdf_block}{context_hint}【本段逐字稿原文】：\n{chunk}"
                
                try:
                    res = self.llm.generate(model=model_name, prompt=full_prompt, options=options)
                    
                    corrected = res
                    expl = ""
                    if "---" in res:
                        parts = res.split("---", 1)
                        corrected = parts[0].strip()
                        expl = parts[1].strip()
                        
                    if len(corrected) < len(chunk) * self.VERBATIM_THRESHOLD:
                        self.log(f"⚠️ 片段 {c_idx+1} 觸發守衛: 過短，保留原文", "warn")
                        full_corrected.append(chunk)
                    else:
                        full_corrected.append(corrected)
                        if expl:
                            cleaned_lines = []
                            seen_last = None
                            for line in expl.splitlines():
                                s = line.strip()
                                s_lower = s.lower().replace("*", "").replace(":", "").strip()
                                if s_lower in ("explanation of changes", "彙整修改日誌", "修改說明", "修改日誌"):
                                    continue
                                if s == seen_last: continue
                                seen_last = s
                                cleaned_lines.append(line)
                            cleaned = "\n".join(cleaned_lines).strip()
                            if cleaned: full_logs.append(cleaned)
                            
                except Exception as e:
                    self.log(f"❌ 片段 {c_idx+1} 失敗: {e}", "error")
                    full_corrected.append(chunk)
                    
            self.finish_spinner(pbar, stop_tick, t)
            
            # --- Save Output ---
            final_doc = "\n".join(full_corrected)
            if full_logs:
                final_doc += f"\n\n---\n\n## 📋 彙整修改日誌\n\n" + "\n\n".join(full_logs)
                
            out_path = os.path.join(self.dirs["p2"], subj, f"{base_name}.md")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(final_doc)
                
            out_hash = self.state_manager.get_file_hash(out_path)
            self.state_manager.update_task(subj, fname, "p2", status="✅", 
                                           char_count=len(final_doc), output_hash=out_hash)
            self.log(f"✅ [{idx}/{len(tasks)}] 校對完成：{fname}")

            # 暫停機制：每個任務完成後檢查是否要 checkpoint
            if self.stop_requested:
                if self.pause_requested and idx < len(tasks):
                    next_task = tasks[idx]  # idx 已是 1-based，下一個剛好
                    self.save_checkpoint(next_task["subject"], next_task["filename"])
                break
            
        for m in models_used:
            self.llm.unload_model(m, logger=self)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    args = parser.parse_args()
    Phase2Proofread().run(force=args.force, subject=args.subject)
