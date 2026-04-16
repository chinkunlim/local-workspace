# -*- coding: utf-8 -*-
import sys, os

import os, sys
# Workspace Root Resolver
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
_workspace_root = os.environ.get("WORKSPACE_DIR", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../..")))

import os
import re
import datetime
from core import PipelineBase
from core.text_utils import smart_split

class Phase5NotionSynthesis(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p5", phase_name="Notion 知識合成", logger=None)
        
    def _clean_content(self, content: str) -> str:
        if "## 📋 Phase 3 修改日誌" in content:
            content = content.split("## 📋 Phase 3 修改日誌", 1)[0].rstrip().rstrip("-").strip()
        return re.sub(r'==(.+?)==', r'\1', content, flags=re.DOTALL)

    def _validate_mermaid(self, text: str) -> list:
        errors = []
        blocks = re.findall(r'```mermaid(.*?)```', text, re.DOTALL)
        for idx, block in enumerate(blocks, 1):
            if 'mindmap' not in block:
                errors.append(f"區塊 {idx}: 缺少 'mindmap' 宣告，心智圖語法無效。")
        return errors

    def _agentic_mermaid_retry(self, node_text: str, base_prompt: str, model: str, options: dict) -> str:
        """Agentic loop to fix Mermaid syntax errors."""
        max_retries = self.config_manager.get_nested("context", "phase5_mermaid_retry_max")
        if max_retries is None:
            raise RuntimeError("voice-memo context.phase5_mermaid_retry_max is missing")
        for attempt in range(1, max_retries + 1):
            errors = self._validate_mermaid(node_text)
            if not errors: return node_text, None # Success
            
            error_str = "\n".join(errors)
            self.log(f"⚠️ [Agentic Retry {attempt}/{max_retries}] 偵測到 Mermaid 語效錯誤: {error_str}", "warn")
            
            retry_prompt = (
                f"{base_prompt}\n\n"
                f"【上次生成的內容有語法錯誤。請修正以下 Mermaid 錯誤並重新輸出整份筆記】：\n{error_str}\n\n"
                f"【你的上一次輸出】：\n{node_text}"
            )
            
            pbar, stop_tick, t = self.create_spinner(f"Agentic 自我修正 ({attempt})")
            try:
                node_text = self.llm.generate(model=model, prompt=retry_prompt, options=options)
            except Exception as e:
                self.log(f"❌ Retry LLM 失敗: {e}", "error")
                break
            finally:
                self.finish_spinner(pbar, stop_tick, t)
            
        # Check again after retries
        errors = self._validate_mermaid(node_text)
        if errors:
            self.log(f"❌ 多次修正後仍然失敗格式: {errors}", "error")
            return node_text, "Mermaid語法失效"
        return node_text, "自癒修正成功"

    def _synthesize_chunked(self, content, map_tpl, reduce_tpl, model, options, label, map_size):
        chunks = smart_split(content, map_size)
        tc = len(chunks)
        self.log(f"   📦 大型逐字稿（{len(content):,} 字元），啟動 Map-Reduce ({tc} 個分塊)")
        
        map_results = []
        map_success = 0
        for ci, chunk in enumerate(chunks, 1):
            self.log(f"   🗂  Map [{ci}/{tc}]：提取關鍵材料...")
            prompt = map_tpl.replace("{INPUT_CONTENT}", chunk) if "{INPUT_CONTENT}" in map_tpl else f"{map_tpl}\n\n<transcript>\n{chunk}\n</transcript>"
            
            pbar, stop_tick, t = self.create_spinner(f"Map {ci}/{tc} ({label})")
            try:
                extracted = self.llm.generate(model=model, prompt=prompt, options=options)
                map_results.append(f"<!-- 分塊 {ci}/{tc} -->\n{extracted.strip()}")
                map_success += 1
            except Exception as e:
                self.log(f"   ⚠️  Map [{ci}/{tc}] 失敗: {e}，跳過。", "warn")
            finally:
                self.finish_spinner(pbar, stop_tick, t)
                
        if not map_results: raise ValueError("Map 階段全部失敗。")
        
        cmb = "\n\n---\n\n".join(map_results)
        note = "以下是按段落提取的關鍵材料。請整合成一份 Notion 筆記。\n\n"
        
        fin_prompt = reduce_tpl.replace("{INPUT_CONTENT}", note + cmb) if "{INPUT_CONTENT}" in reduce_tpl else f"{reduce_tpl}\n\n<materials>\n{note}{cmb}\n</materials>"
        
        self.log(f"   🔗 Reduce：整合 {len(map_results)} 份摘要...")
        pbar, stop_tick, t = self.create_spinner(f"Reduce ({label})")
        try:
            final_note = self.llm.generate(model=model, prompt=fin_prompt, options=options)
        finally:
            self.finish_spinner(pbar, stop_tick, t)
            
        return final_note, map_success, tc

    def run(self, force=False, subject=None, resume_from=None):
        self.log(f"✨ 啟動 Phase 5：Notion 知識合成")
        reduce_tpl = self.get_prompt("Phase 5: 筆記合成指令")
        map_tpl = self.get_prompt("Phase 5 Part A: 分塊摘要提取指令")
        if not reduce_tpl:
            self.log("❌ 找不到 Phase 5 prompt", "error")
            return
        if not map_tpl:
            self.log("⚠️ 找不到 Phase 5 Part A prompt，使用 Reduce 替代", "warn")
            map_tpl = reduce_tpl

        tasks = self.get_tasks(prev_phase_key="p4", force=force, subject_filter=subject, resume_from=resume_from)
        if not tasks: return

        self.log(f"📋 共有 {len(tasks)} 個檔案待合成。")
        models_used = set()

        for idx, task in enumerate(tasks, 1):
            if self.check_system_health(): break

            subj, fname = task["subject"], task["filename"]
            
            config = self.get_config("phase5", subject_name=subj)
            model = config.get("model")
            options = config.get("options", {})
            chunk_thresh = config.get("chunk_threshold")
            map_size = config.get("map_chunk_size")
            if not model:
                raise RuntimeError(f"phase5 config missing model for {subj}")
            if chunk_thresh is None or map_size is None:
                raise RuntimeError(f"phase5 config missing chunk thresholds for {subj}")
            models_used.add(model)
            
            base_name = os.path.splitext(fname)[0]
            m = re.match(r'^(.+)-(\d+)$', base_name)
            lecture_base = m.group(1) if m else base_name

            in_path = os.path.join(self.dirs["p4"], subj, f"{lecture_base}.md")
            out_path = os.path.join(self.dirs["p5"], subj, f"{lecture_base}.md")
            
            if not os.path.exists(in_path):
                self.log(f"⚠️ 找不到來源：{in_path}", "warn")
                continue

            with open(in_path, "r", encoding="utf-8") as f:
                content = self._clean_content(f.read())

            self.log(f"📝 [{idx}/{len(tasks)}] 生成筆記：[{subj}] {lecture_base}.md ({len(content)} 字元)")

            try:
                note_tag = None
                if len(content) > chunk_thresh:
                    res, sc, tc = self._synthesize_chunked(content, map_tpl, reduce_tpl, model, options, lecture_base, map_size)
                    yaml_mr = "true"
                    yaml_chk = f"{sc}/{tc}"
                    if sc < tc:
                        note_tag = f"Map {sc}/{tc} 成功 (缺損)"
                        self.log(f"⚠️ {note_tag}", "warn")
                else:
                    pmpt = reduce_tpl.replace("{INPUT_CONTENT}", content) if "{INPUT_CONTENT}" in reduce_tpl else f"{reduce_tpl}\n\n<transcript>\n{content}\n</transcript>"
                    pbar, stop_tick, t = self.create_spinner(f"合成 ({lecture_base})")
                    try: res = self.llm.generate(model=model, prompt=pmpt, options=options)
                    finally: self.finish_spinner(pbar, stop_tick, t)
                    yaml_mr = "false"
                    yaml_chk = "N/A"

                # Agentic Mermaid Retry
                res, mm_tag = self._agentic_mermaid_retry(res, reduce_tpl, model, options)
                if mm_tag and not note_tag: note_tag = mm_tag

                # YAML
                now_str = datetime.datetime.now().isoformat('T', 'seconds')
                yaml_header = f"---\nsubject: {subj}\nlecture: {lecture_base}\ngenerated_at: {now_str}\nmodel: {model}\nmap_reduce: {yaml_mr}\nmap_chunks: {yaml_chk}\nsource_chars: {len(content)}\noutput_chars: {len(res)}\npipeline_version: v7.0-OOP\n---\n\n"
                
                final_doc = yaml_header + res

                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(final_doc)

                out_hash = self.state_manager.get_file_hash(out_path)
                self.state_manager.update_task(subj, fname, "p5", char_count=len(final_doc), note_tag=note_tag, output_hash=out_hash)
                
                self.log(f"✅ [{idx}/{len(tasks)}] 筆記完成：{lecture_base}.md")

                # 暫停機制：每個任務完成後檢查是否要 checkpoint
                if self.stop_requested:
                    if self.pause_requested and idx < len(tasks):
                        next_task = tasks[idx]  # idx 已是 1-based，下一個剛好
                        self.save_checkpoint(next_task["subject"], next_task["filename"])
                    break

            except Exception as e:
                self.log(f"❌ 合成失敗 {lecture_base}.md: {e}", "error")

        for m in models_used:
            self.llm.unload_model(m, logger=self)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    args = parser.parse_args()
    Phase5NotionSynthesis().run(force=args.force, subject=args.subject)
