# -*- coding: utf-8 -*-
"""
Phase 1: High-Precision Audio Transcription
Refactored to V7.0 OOP Architecture
"""
import sys, os

import os, sys
# Workspace Root Resolver
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
_workspace_root = os.environ.get("WORKSPACE_DIR", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../..")))

import os
from core import PipelineBase

class Phase1Transcribe(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p1", phase_name="語音轉錄", logger=None)
        
    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.log("🚀 啟動 Phase 1：語音轉錄")
        
        # Sandbox HuggingFace to strictly inside the project
        openclaw_root = os.path.abspath(os.path.join(self.base_dir, "..", ".."))
        model_dir = os.path.join(openclaw_root, "models")
        os.makedirs(model_dir, exist_ok=True)
        os.environ["HF_HOME"] = model_dir
        os.environ["HF_HUB_CACHE"] = model_dir
        
        model = None
        current_model_name = None
        
        tasks = self.get_tasks(force=force, subject_filter=subject, file_filter=file_filter, single_mode=single_mode, resume_from=resume_from)
        
        if not tasks:
            self.log("📋 Phase 1 沒有待轉錄的音檔。")
            return
            
        self.log(f"📋 Phase 1 共有 {len(tasks)} 個音檔待轉錄。")
        
        for idx, task in enumerate(tasks, 1):
            if self.check_system_health(): break
            
            subj, fname = task["subject"], task["filename"]
            
            config = self.get_config("phase1", subject_name=subj)
            engine = config.get("engine", "faster-whisper").lower()
            model_name = config.get("model", "medium")
            device = config.get("device", "cpu")
            compute_type = config.get("compute_type", "int8")
            beam_size = int(config.get("beam_size", 5))
            
            # Re-load model if profile changes between subjects
            if model is not None and current_model_name != model_name:
                model = None
            current_model_name = model_name
            
            base_name = fname.replace(".m4a", "")
            audio_path = os.path.join(self.dirs["p0"], subj, fname)
            pure_out_path = os.path.join(self.dirs["p1"], subj, f"{base_name}.md")
            ts_out_path = os.path.join(self.dirs["p1"], subj, f"{base_name}_timestamped.md")
            
            os.makedirs(os.path.dirname(pure_out_path), exist_ok=True)
            
            self.log(f"🎙️ [{idx}/{len(tasks)}] 正在處理：[{subj}] {fname}")
            
            if model is None:
                if engine == "faster-whisper":
                    try: from faster_whisper import WhisperModel
                    except ImportError:
                        self.log("❌ 找不到 faster_whisper。請安裝: pip3 install faster-whisper", "error")
                        return
                    self.log(f"🧠 載入 Whisper ({engine}) {model_name}...")
                    model = WhisperModel(model_name, device=device, compute_type=compute_type, download_root=model_dir)
                elif engine == "mlx-whisper":
                    try: import mlx_whisper
                    except ImportError:
                        self.log("❌ 找不到 mlx_whisper。請安裝: pip3 install mlx-whisper", "error")
                        return
                    self.log(f"🧠 備妥 Whisper ({engine}) {model_name}...")
                    
            try:
                pure_text = ""
                ts_text = ""
                
                if engine == "mlx-whisper":
                    import mlx_whisper
                    import warnings
                    pbar, stop_tick, t = self.create_spinner(f"轉錄處理 ({fname})")
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        result = mlx_whisper.transcribe(audio_path, path_or_hf_repo=model_name, verbose=False)
                    self.finish_spinner(pbar, stop_tick, t)
                    
                    segments = result.get("segments", [])
                else:
                    from tqdm import tqdm
                    segments_gen, info = model.transcribe(audio_path, beam_size=beam_size, vad_filter=True)
                    duration = int(info.duration)
                    last_end = 0
                    segments = []
                    with tqdm(total=duration, desc=f"轉錄進度 ({fname})", unit="秒", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
                        for s in segments_gen:
                            inc = int(s.end) - last_end
                            if inc > 0:
                                pbar.update(inc)
                                last_end = int(s.end)
                            segments.append(s)
                        if last_end < duration:
                            pbar.update(duration - last_end)
                            
                for s in segments:
                    text_val = s["text"] if isinstance(s, dict) else s.text
                    start_val = s["start"] if isinstance(s, dict) else s.start
                    end_val = s["end"] if isinstance(s, dict) else s.end
                    
                    pure_text += text_val.strip() + "\n"
                    start_m, start_s = int(start_val // 60), int(start_val % 60)
                    end_m, end_s = int(end_val // 60), int(end_val % 60)
                    ts_text += f"[{start_m:02d}:{start_s:02d}] - [{end_m:02d}:{end_s:02d}] {text_val.strip()}\n"
                    
                with open(pure_out_path, "w", encoding="utf-8") as f:
                    f.write(pure_text)
                with open(ts_out_path, "w", encoding="utf-8") as f:
                    f.write(ts_text)
                    
                # DAG 追蹤: 紀錄輸出的 hash
                out_hash = self.state_manager.get_file_hash(pure_out_path)
                self.state_manager.update_task(subj, fname, "p1", status="✅", output_hash=out_hash)
                
                self.log(f"✅ [{idx}/{len(tasks)}] 轉錄完成：{fname}")

                # 暫停機制：每個任務完成後檢查是否要 checkpoint
                if self.stop_requested:
                    if self.pause_requested and idx < len(tasks):
                        next_task = tasks[idx]  # idx 已是 1-based，下一個剛好
                        self.save_checkpoint(next_task["subject"], next_task["filename"])
                    break
                
            except Exception as e:
                self.log(f"❌ 轉錄失敗 {fname}: {e}", "error")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    args = parser.parse_args()
    Phase1Transcribe().run(force=args.force, subject=args.subject)
