import os
import sys

# Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import AtomicWriter, PipelineBase
from core.orchestration.human_gate import VerificationGate
from core.services.sm2 import SM2Engine
from core.utils.file_utils import write_csv_safe  # #10 Shared CSV utility


class Phase2Anki(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="p2", phase_name="Anki 卡片生成", skill_name="academic_edu_assistant"
        )
        self.prev_phase = "p1"

        # AnkiConnect config (#9)
        anki_cfg = self.config_manager.get_section("ankiconnect") or {}
        self.ankiconnect_enabled = bool(anki_cfg.get("enabled", False))
        self.ankiconnect_url = anki_cfg.get("url", "http://127.0.0.1:8765")
        self.ankiconnect_deck = anki_cfg.get("deck", "OpenClaw::Imported")
        self.ankiconnect_model = anki_cfg.get("note_model", "Basic")

        # SM-2 Engine
        self.sm2_engine = SM2Engine(self.workspace_root)

    # ------------------------------------------------------------------ #
    #  AnkiConnect Push (#9)                                               #
    # ------------------------------------------------------------------ #

    def _push_to_anki(self, csv_content: str, deck_name: str) -> int:
        """Parse CSV content and push cards to Anki via AnkiConnect API.

        Args:
            csv_content: Raw CSV text from LLM output (format: 問題,答案)
            deck_name:   Target Anki deck name (overrides config default)

        Returns:
            Number of cards successfully added.
        """
        import json

        import requests as _req

        lines = [ln.strip() for ln in csv_content.splitlines() if ln.strip() and "," in ln]
        notes = []
        for line in lines:
            # Simple CSV split; handles quoted fields via maxsplit heuristic
            parts = line.split(",", 1)
            if len(parts) != 2:
                continue
            front = parts[0].strip().strip('"')
            back = parts[1].strip().strip('"')
            if not front or not back:
                continue
            notes.append(
                {
                    "deckName": deck_name,
                    "modelName": self.ankiconnect_model,
                    "fields": {"Front": front, "Back": back},
                    "options": {"allowDuplicate": False},
                    "tags": ["openclaw"],
                }
            )

        if not notes:
            self.warning("⚠️ [AnkiConnect] 無有效卡片可推送")
            return 0

        payload = json.dumps(
            {
                "action": "addNotes",
                "version": 6,
                "params": {"notes": notes},
            }
        )
        try:
            resp = _req.post(self.ankiconnect_url, data=payload, timeout=10)
            resp.raise_for_status()
            result = resp.json()
            added = sum(1 for r in (result.get("result") or []) if r is not None)
            errors = [r for r in (result.get("result") or []) if r is None]
            if errors:
                self.warning(f"⚠️ [AnkiConnect] {len(errors)} 張卡片重複或失敗")
            return added
        except Exception as exc:
            self.warning(f"⚠️ [AnkiConnect] 推送失敗: {exc}")
            return 0

    # ------------------------------------------------------------------ #
    #  File Processing                                                     #
    # ------------------------------------------------------------------ #

    def _process_file(self, idx: int, task: dict, total: int):
        subj = task["subject"]
        fname = task["filename"]

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
        model_name = self.config_manager.get_nested("models", "default") or "qwen3:8b"
        pbar, stop_tick, t = self.create_spinner(f"生成 Anki 卡片 ({fname}) using {model_name}...")
        try:
            response = self.llm.generate(model=model_name, prompt=prompt)
        except Exception as e:
            self.error(f"❌ 生成失敗: {e}")
            return
        finally:
            self.finish_spinner(pbar, stop_tick, t)
            self.llm.unload_model(model_name, logger=self)

        out_dir = os.path.join(self.base_dir, "output", "02_anki")
        os.makedirs(out_dir, exist_ok=True)

        stem = os.path.splitext(fname)[0]
        out_path = os.path.join(out_dir, f"{stem}.csv")

        # F3: Use write_csv_safe so commas/quotes inside card content are properly escaped.
        # Re-parse LLM output to build typed rows for the csv module.
        csv_text = response.strip()

        # --- Verification Gate: human reviews generated Anki cards before finalising ---
        self.info("⏸️  [Verification Gate] 正在開啟 Anki 卡片審核視窗...")
        gate = VerificationGate(
            skill_name="academic_edu_assistant / p02_anki",
            original_text=content,  # source comparison report (left pane)
            llm_text=csv_text,  # LLM-generated CSV (right pane, editable)
        )
        approved = gate.start()
        if approved and approved.strip():
            csv_text = approved
            self.info("✅ [Verification Gate] 人工審核完成，使用核准內容。")
        else:
            self.info("⚠️  [Verification Gate] 未提交，保留 LLM 生成結果。", "warn")

        csv_rows = []
        for line in csv_text.splitlines():
            line = line.strip()
            if not line or "," not in line:
                continue
            parts = line.split(",", 1)
            if len(parts) == 2:
                csv_rows.append([parts[0].strip().strip('"'), parts[1].strip().strip('"')])

        from core.utils.file_utils import write_csv_safe

        write_csv_safe(path=out_path, rows=csv_rows, logger=self)
        self.info(f"✅ Anki 卡片已匯出: {out_path} ({len(csv_rows)} 筆)")

        # Integrate with local SM-2 engine for Telegram pushing
        deck = f"{self.ankiconnect_deck}::{subj}"
        sm2_added = 0
        for front, back in csv_rows:
            self.sm2_engine.add_card(front, back, deck)
            sm2_added += 1
        self.info(f"💾 成功新增 {sm2_added} 張卡片至 SM-2 排程引擎")

        # #9: Push to AnkiConnect if enabled (pass raw csv_text so _push_to_anki re-parses)
        if self.ankiconnect_enabled:
            deck = f"{self.ankiconnect_deck}::{subj}"
            added = self._push_to_anki(csv_text, deck_name=deck)
            if added:
                self.info(
                    f"\U0001f3b4 [AnkiConnect] \u6210\u529f\u63a8\u9001 {added} \u5f35\u5361\u7247 \u2192 \u724c\u7d44\u300c{deck}\u300d"
                )

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
