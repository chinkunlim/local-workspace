"""
Phase 2: Context-Aware Proofreading
Refactored to V7.0 OOP Architecture
"""

# Group 1 — stdlib
import os
import re
import sys

# Group 2 — Internal Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

# Group 3 — third-party
from pypdf import PdfReader

# Group 4 — Core imports
from core import AtomicWriter, PipelineBase
from core.text_utils import smart_split


class Phase2Proofread(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p2", phase_name="上下文校對", logger=None)
        lookback = self.config_manager.get_nested("context", "phase2_lookback_chars")
        if lookback is None:
            raise RuntimeError("audio-transcriber context.phase2_lookback_chars is missing")
        self.LOOKBACK_CHARS = int(lookback)
        threshold = self.config_manager.get_nested("thresholds", "phase2_verbatim")
        if threshold is None:
            raise RuntimeError("audio-transcriber thresholds.phase2_verbatim is missing")
        self.VERBATIM_THRESHOLD = float(threshold)

        # Proofread Feedback Loop config (#8)
        fb_cfg = self.config_manager.get_section("phase2_feedback") or {}
        self.feedback_enabled = bool(fb_cfg.get("enabled", False))
        self.feedback_threshold = float(fb_cfg.get("confidence_threshold", 0.70))
        self.feedback_secondary_model = fb_cfg.get("secondary_model", "")

    def _get_glossary(self, subject: str) -> str:
        import json

        ref_dir = self.dirs.get("p0_ref", os.path.join(self.base_dir, "output", "00_glossary"))
        glossary_path = os.path.join(ref_dir, subject, "glossary.json")
        if not os.path.exists(glossary_path):
            return ""
        try:
            with open(glossary_path, encoding="utf-8") as f:
                gloss = json.load(f)
            if not gloss:
                return ""
            lines = [f"  「{k}」→「{v}」" for k, v in gloss.items()]
            self.log(f"📚 已載入詞庫 ({subject}/glossary.json，共 {len(gloss)} 筆)")
            return "【術語詞庫 — Whisper 聽寫修正對照表】：\n" + "\n".join(lines)
        except Exception as e:
            self.log(f"⚠️ 詞庫載入失敗: {e}", "warn")
            return ""

    def _apply_glossary_regex(self, text: str, subject: str) -> str:
        """#5 Deterministic Terminology: hard-enforce glossary corrections via Regex.

        After LLM proofreads, this pass iterates over glossary.json and uses
        re.sub to replace any remaining incorrect terms with their canonical forms.
        This is non-probabilistic and guarantees terminology consistency.
        """
        import json

        ref_dir = self.dirs.get("p0_ref", os.path.join(self.base_dir, "output", "00_glossary"))
        glossary_path = os.path.join(ref_dir, subject, "glossary.json")
        if not os.path.exists(glossary_path):
            return text
        try:
            with open(glossary_path, encoding="utf-8") as f:
                gloss = json.load(f)
        except Exception:
            return text

        replacements = 0
        for wrong, correct in gloss.items():
            if wrong.strip() == correct.strip():
                continue
            # Escape the wrong term for regex safety
            pattern = re.escape(wrong)
            new_text, n = re.subn(pattern, correct, text)
            if n:
                text = new_text
                replacements += n

        if replacements:
            self.log(f"🔄 [Regex术語修正] 共強制替換 {replacements} 處術語")
        return text

    def _proofread_with_feedback(
        self,
        model_name: str,
        prompt: str,
        chunk: str,
        options: dict,
        c_idx: int,
    ) -> str:
        """#8 Proofread Feedback Loop.

        Performs primary LLM proofreading. If the confidence score
        (output/input length ratio) falls below self.feedback_threshold,
        automatically re-runs with self.feedback_secondary_model.
        Returns the best corrected text, falling back to original chunk on total failure.
        """

        def _call(m: str) -> str:
            return self.llm.generate(model=m, prompt=prompt, options=options)

        try:
            primary_result = _call(model_name)
        except Exception as e:
            self.log(f"❌ [主要模型] 片段 {c_idx + 1} 失敗: {e}", "error")
            return chunk

        ratio = len(primary_result.strip()) / max(len(chunk), 1)

        if (
            self.feedback_enabled
            and ratio < self.feedback_threshold
            and self.feedback_secondary_model
        ):
            self.log(
                f"⚠️ [回饋修正環] 片段 {c_idx + 1} 信心分 {ratio:.2f} < {self.feedback_threshold:.2f}，"
                f"啟動備用模型 {self.feedback_secondary_model}...",
                "warn",
            )
            try:
                secondary_result = _call(self.feedback_secondary_model)
                secondary_ratio = len(secondary_result.strip()) / max(len(chunk), 1)
                models_used_ref = getattr(self, "_current_models_used", None)
                if models_used_ref is not None:
                    models_used_ref.add(self.feedback_secondary_model)
                # H4: If secondary model ALSO fails confidence, trigger HITL
                if secondary_ratio < self.feedback_threshold:
                    self.log(
                        f"\u26a0\ufe0f [H4/HITL] \u5099\u7528\u6a21\u578b\u4fe1\u5fc3\u5206\u4e5f\u4f4e ({secondary_ratio:.2f})\uff0c\u89f8\u767c HITL \u4ecb\u5165...",
                        "warn",
                    )
                    try:
                        from core.hitl_manager import HITLEvent, HITLManager
                        from core.telegram_bot import send_hitl_prompt

                        hitl_mgr = HITLManager(base_dir=self.base_dir)
                        event = HITLEvent(
                            phase="p2_proofread",
                            skill_name="audio-transcriber",
                            reason=(
                                f"\u7247\u6bb5 {c_idx + 1}: \u4e3b\u8981\u6a21\u578b ({model_name}) \u548c\u5099\u7528\u6a21\u578b "
                                f"({self.feedback_secondary_model}) \u4fe1\u5fc3\u5206\u5747\u4f4e\u65bc\u95b3\u5024 "
                                f"{self.feedback_threshold:.2f}"
                            ),
                            payload={
                                "chunk_index": c_idx,
                                "primary_ratio": round(ratio, 3),
                                "secondary_ratio": round(secondary_ratio, 3),
                                "chunk_preview": chunk[:200],
                            },
                        )
                        hitl_mgr.trigger(event)
                        send_hitl_prompt(
                            trace_id=event.trace_id,
                            phase=event.phase,
                            reason=event.reason,
                        )
                    except Exception as _hitl_exc:
                        self.log(
                            f"\u26a0\ufe0f [HITL] \u7121\u6cd5\u767c\u9001\u4e8b\u4ef6: {_hitl_exc}",
                            "warn",
                        )
                return secondary_result
            except Exception as e:
                self.log(
                    f"\u26a0\ufe0f [\u56de\u994b\u4fee\u6b63\u74b0] \u5099\u7528\u6a21\u578b\u5931\u6557: {e}\uff0c\u4fdd\u7559\u4e3b\u8981\u6a21\u578b\u7d50\u679c",
                    "warn",
                )

        return primary_result

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.log("🧠 啟動 Phase 2：校對模式")
        prompt_tpl = self.get_prompt("Phase 2: 校對指令")

        tasks = self.get_tasks(
            prev_phase_key="p1",
            force=force,
            subject_filter=subject,
            file_filter=file_filter,
            single_mode=single_mode,
            resume_from=resume_from,
        )

        if not tasks:
            self.log("📋 Phase 2 沒有待校對的檔案。")
            return

        self.log(f"📋 Phase 2 共有 {len(tasks)} 個檔案待校對。")
        models_used = set()
        self._current_models_used = models_used  # expose to _proofread_with_feedback (#8)

        try:
            for idx, task in enumerate(tasks, 1):
                if self.check_system_health():
                    break

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
                ref_dir = self.dirs.get(
                    "p0_ref", os.path.join(self.base_dir, "output", "00_glossary")
                )
                pdf_path = os.path.join(ref_dir, subj, f"{base_name}.pdf")

                if os.path.exists(pdf_path):
                    try:
                        reader = PdfReader(pdf_path)
                        pdf_text = "\n".join(
                            [p.extract_text() for p in reader.pages[:20] if p.extract_text()]
                        )[:20000]
                        self.log(f"📖 已載入 PDF 參考 ({len(pdf_text)} 字元)")
                    except Exception as e:
                        self.log(f"⚠️ PDF 讀取錯誤: {e}", "warn")
                else:
                    m = re.match(r"^(.+)-(\d+)$", base_name)
                    if m:
                        lecture_base = m.group(1)
                        shared_pdf = os.path.join(ref_dir, subj, f"{lecture_base}.pdf")
                        if os.path.exists(shared_pdf):
                            try:
                                reader = PdfReader(shared_pdf)
                                pdf_text = "\n".join(
                                    [
                                        p.extract_text()
                                        for p in reader.pages[:20]
                                        if p.extract_text()
                                    ]
                                )[:20000]
                                self.log(f"📖 已載入共用 PDF ({lecture_base}.pdf)")
                            except Exception:
                                pass

                # --- Load P1 Transform ---
                in_path = os.path.join(self.dirs["p1"], subj, f"{base_name}.md")
                if not os.path.exists(in_path):
                    self.log(f"⚠️ 找不到 P1 來源: {in_path}", "warn")
                    continue

                with open(in_path, encoding="utf-8") as f:
                    raw_text = f.read()

                chunks = smart_split(raw_text, chunk_size)
                full_corrected = []
                full_logs = []

                # #6 Granular Checkpointing: resume from last completed chunk
                resume_chunk = self.state_manager.load_chunk_checkpoint(subj, fname, "p2")
                if resume_chunk is not None:
                    self.log(
                        f"⏭️  [Chunk Resume] 從片段 {resume_chunk + 1} 繼續（跳過 0~{resume_chunk}）"
                    )

                self.log(
                    f"📦 [{idx}/{len(tasks)}] 正在校對：[{subj}] {base_name}.md (共分為 {len(chunks)} 段)"
                )

                pbar, stop_tick, t = self.create_spinner(f"\u6821\u5c0d ({fname})")

                # A2: Build all prompts first, then fire async batch generation
                # Prompts that should be skipped (checkpoint resume) get empty string placeholder.
                prompts_to_run: list[str] = []
                skip_flags: list[bool] = []
                for c_idx, chunk in enumerate(chunks):
                    if resume_chunk is not None and c_idx <= resume_chunk:
                        prompts_to_run.append("")
                        skip_flags.append(True)
                        continue
                    skip_flags.append(False)
                    context_hint = ""
                    if c_idx > 0:
                        prev_tail = raw_text[
                            max(0, c_idx * chunk_size - self.LOOKBACK_CHARS) : c_idx * chunk_size
                        ]
                        context_hint = f"[\u524d\u6bb5\u7d50\u5c3e\u4e0a\u4e0b\u6587\uff08\u50c5\u4f9b\u53c3\u8003\uff0c\u8acb\u52ff\u5728\u8f38\u51fa\u4e2d\u91cd\u8907\u6b64\u6bb5\uff09]\uff1a\n...{prev_tail}\n\n"
                    pdf_block = (
                        f"[\u8b1b\u7fa9 PDF \u53c3\u8003]\uff1a\n{pdf_text}\n\n" if pdf_text else ""
                    )
                    gloss_block = f"{glossary_text}\n\n" if glossary_text else ""
                    prompts_to_run.append(
                        f"{prompt_tpl}\n\n{gloss_block}{pdf_block}{context_hint}"
                        f"[\u672c\u6bb5\u9010\u5b57\u7a3f\u539f\u6587]\uff1a\n{chunk}"
                    )

                # Execute concurrently (max 3 in-flight to prevent OOM)
                import asyncio

                raw_responses = asyncio.run(
                    self.llm.async_batch_generate(
                        model=model_name,
                        prompts=prompts_to_run,
                        options=options,
                        max_concurrency=3,
                        logger=self,
                    )
                )

                for c_idx, (chunk, res, skipped) in enumerate(
                    zip(chunks, raw_responses, skip_flags)
                ):
                    if skipped:
                        full_corrected.append(chunk)
                        continue

                    if self.check_system_health():
                        self.state_manager.save_chunk_checkpoint(
                            subj, fname, "p2", chunk_index=c_idx - 1
                        )
                        break

                    # If async call failed (returns ""), fall back to _proofread_with_feedback
                    if not res:
                        res = self._proofread_with_feedback(
                            model_name=model_name,
                            prompt=prompts_to_run[c_idx],
                            chunk=chunk,
                            options=options,
                            c_idx=c_idx,
                        )

                    corrected = res
                    expl = ""
                    if "---" in res:
                        parts_res = res.split("---", 1)
                        corrected = parts_res[0].strip()
                        expl = parts_res[1].strip()

                    if len(corrected) < len(chunk) * self.VERBATIM_THRESHOLD:
                        self.log(
                            f"\u26a0\ufe0f \u7247\u6bb5 {c_idx + 1} \u89f8\u767c\u5b88\u885b: \u904e\u77ed\uff0c\u4fdd\u7559\u539f\u6587",
                            "warn",
                        )
                        full_corrected.append(chunk)
                    else:
                        corrected = self._apply_glossary_regex(corrected, subj)
                        full_corrected.append(corrected)
                        if expl:
                            cleaned_lines = []
                            seen_last = None
                            for line in expl.splitlines():
                                s = line.strip()
                                s_lower = s.lower().replace("*", "").replace(":", "").strip()
                                if s_lower in (
                                    "explanation of changes",
                                    "\u5f59\u6574\u4fee\u6539\u65e5\u8a8c",
                                    "\u4fee\u6539\u8aaa\u660e",
                                    "\u4fee\u6539\u65e5\u8a8c",
                                ):
                                    continue
                                if s == seen_last:
                                    continue
                                seen_last = s
                                cleaned_lines.append(line)
                            cleaned = "\n".join(cleaned_lines).strip()
                            if cleaned:
                                full_logs.append(cleaned)

                    # Throttled checkpoint every 5 chunks
                    if (c_idx + 1) % 5 == 0:
                        self.state_manager.save_chunk_checkpoint(
                            subj, fname, "p2", chunk_index=c_idx
                        )

                self.finish_spinner(pbar, stop_tick, t)

                # --- Save Output ---
                final_doc = "\n".join(full_corrected)
                if full_logs:
                    final_doc += "\n\n---\n\n## 📋 彙整修改日誌\n\n" + "\n\n".join(full_logs)

                out_path = os.path.join(self.dirs["p2"], subj, f"{base_name}.md")
                os.makedirs(os.path.dirname(out_path), exist_ok=True)

                AtomicWriter.write_text(out_path, final_doc)

                out_hash = self.state_manager.get_file_hash(out_path)
                self.state_manager.update_task(
                    subj, fname, "p2", status="✅", char_count=len(final_doc), output_hash=out_hash
                )
                # Clear chunk checkpoint on successful file completion
                self.state_manager.clear_chunk_checkpoint(subj, fname, "p2")
                self.log(f"✅ [{idx}/{len(tasks)}] 校對完成：{fname}")

                # 暫停機制：每個任務完成後檢查是否要 checkpoint
                if self.stop_requested:
                    if self.pause_requested and idx < len(tasks):
                        next_task = tasks[idx]  # idx 已是 1-based，下一個剛好
                        self.save_checkpoint(next_task["subject"], next_task["filename"])
                    break

        finally:
            for m in models_used:
                self.llm.unload_model(m, logger=self)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    args = parser.parse_args()
    Phase2Proofread().run(force=args.force, subject=args.subject)
