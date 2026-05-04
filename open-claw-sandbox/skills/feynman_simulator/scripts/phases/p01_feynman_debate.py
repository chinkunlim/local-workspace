"""
Phase 1: Feynman Debate Loop
============================
Implements the Feynman Technique as a two-agent dialogue:

  StudentAgent  — Local Ollama model. Reads the raw note and explains
                  it "as if teaching a curious 15-year-old with no prior
                  knowledge of the topic." Plain English, no jargon.

  TutorAgent    — Gemini (via Playwright persistent session). Reads the
                  student's explanation and probes its weaknesses with
                  Socratic questions: "You said X — but *why* does Y
                  follow?", "What breaks this assumption?", etc.

Debate runs for MAX_ROUNDS (default 3). Each round's full exchange is
appended to a Markdown file in data/feynman_simulator/archives/.
The final archive path is emitted so Phase 2 (synthesis) can inject
the debate findings back into the original note.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import os

from core import PhaseBase
from core.ai.llm_client import OllamaClient
from core.utils.playwright_utils import get_persistent_context

MAX_ROUNDS = 3
_STUDENT_MODEL = "qwen3:8b"


class Phase1FeynmanDebate(PhaseBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="p01_feynman_debate",
            phase_name="Feynman Debate Loop (Student ↔ Tutor)",
            skill_name="feynman_simulator",
        )
        self._llm = OllamaClient()

    # ------------------------------------------------------------------ #
    #  StudentAgent — Local Ollama                                         #
    # ------------------------------------------------------------------ #

    def _student_explain(self, note_content: str, tutor_challenge: str | None = None) -> str:
        """Generate a plain-language explanation of the note content.

        On the first round, explains the note from scratch.
        On subsequent rounds, responds to the tutor's challenge.
        """
        if tutor_challenge is None:
            prompt = (
                "你是一個正在自學的大學生。請用最簡單的語言，向一個完全不懂這個主題的15歲朋友"
                "解釋以下筆記的核心概念。\n"
                "- 不能使用專業術語，如果使用，必須立刻用生活化比喻解釋。\n"
                "- 必須說明「為什麼這個概念重要」、「它在現實中的應用是什麼」。\n"
                "- 長度控制在 300 字以內。\n\n"
                f"【筆記內容】\n{note_content}"
            )
        else:
            prompt = (
                "你是一個正在辯護自己理解的大學生。導師剛才對你的解釋提出了質疑：\n\n"
                f"【導師的質疑】\n{tutor_challenge}\n\n"
                "請回應這個質疑：\n"
                "- 承認你解釋中的不足之處。\n"
                "- 修正你的理解，補充更準確的說法。\n"
                "- 若質疑不成立，清楚說明為何你的原始解釋是正確的。\n"
                "- 回應控制在 250 字以內。"
            )
        return self._llm.generate(model=_STUDENT_MODEL, prompt=prompt)

    # ------------------------------------------------------------------ #
    #  TutorAgent — Gemini via Playwright                                  #
    # ------------------------------------------------------------------ #

    async def _tutor_challenge(
        self,
        page,
        student_explanation: str,
        round_num: int,
    ) -> str:
        """Send student explanation to Gemini and return its Socratic challenge."""
        if round_num == 1:
            prompt = (
                "你是一位嚴格的大學教授。你的學生剛才提交了以下解釋。\n"
                "請扮演蘇格拉底，找出解釋中的邏輯漏洞、不精確的類比、或遺漏的關鍵前提。\n"
                "用1到2個具體的反問句來挑戰學生，逼出更深層的理解。\n"
                "不要直接給出答案。\n\n"
                f"【學生的解釋】\n{student_explanation}"
            )
        else:
            prompt = (
                f"（第 {round_num} 輪辯證）\n"
                "學生已回應了你的質疑。請評估他的回應是否更加嚴謹：\n"
                "- 若仍有漏洞，繼續用1個具體問題深挖。\n"
                "- 若解釋已足夠嚴謹，明確讚許並指出哪些方面得到了改善。\n\n"
                f"【學生的最新回應】\n{student_explanation}"
            )

        input_box = page.locator('div[contenteditable="true"]').last
        await input_box.fill(prompt)
        await input_box.press("Enter")

        self.info(f"  ⏳ 等待 Gemini 第 {round_num} 輪回應...")
        await asyncio.sleep(18)

        # Extract the last response block
        responses = await page.locator("message-content").all()
        if responses:
            return await responses[-1].inner_text()

        # Fallback: scrape visible text
        raw = await page.evaluate("document.body.innerText")
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        return "\n".join(lines[-40:])

    # ------------------------------------------------------------------ #
    #  Full Debate Orchestration                                           #
    # ------------------------------------------------------------------ #

    async def _run_debate(self, note_path: str, note_content: str) -> str:
        """Run the full StudentAgent ↔ TutorAgent debate and return archive path."""
        slug = os.path.splitext(os.path.basename(note_path))[0][:30].replace(" ", "_")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = os.path.join(self.base_dir, "archives")
        os.makedirs(archive_dir, exist_ok=True)
        archive_path = os.path.join(archive_dir, f"feynman_{slug}_{ts}.md")

        debate_log: list[str] = [
            f"# Feynman Debate — {slug}",
            f"**Source**: `{note_path}`  \n**Date**: {datetime.now().isoformat()}\n",
            "---\n",
        ]

        self.info(f"\n🎓 開始費曼辯證: {slug}")

        async with get_persistent_context(headless=True) as context:
            page = await context.new_page()
            await page.goto(
                "https://gemini.google.com/app", wait_until="domcontentloaded", timeout=60000
            )
            await page.wait_for_selector('div[contenteditable="true"]', timeout=30000)
            self.info("  ✅ Gemini 連線成功")

            tutor_challenge: str | None = None

            for round_num in range(1, MAX_ROUNDS + 1):
                self.info(f"\n  📖 Round {round_num}/{MAX_ROUNDS}")

                # StudentAgent explains / responds
                self.info("  🧑‍🎓 StudentAgent 思考中...")
                student_resp = self._student_explain(note_content, tutor_challenge)

                debate_log.append(f"## Round {round_num}\n")
                debate_log.append(f"### 🧑‍🎓 Student (Local Ollama)\n\n{student_resp}\n")

                # TutorAgent probes
                self.info("  🎓 TutorAgent (Gemini) 評估中...")
                tutor_resp = await self._tutor_challenge(page, student_resp, round_num)

                debate_log.append(f"### 🎓 Tutor (Gemini)\n\n{tutor_resp}\n\n---\n")

                tutor_challenge = tutor_resp

                # If Gemini signals satisfaction, stop early
                satisfaction_signals = ["已足夠嚴謹", "改善", "excellent", "well done", "correct"]
                if round_num > 1 and any(s in tutor_resp.lower() for s in satisfaction_signals):
                    self.info("  ✅ Gemini 認可理解已達標，提前結束辯證。")
                    break

        # Final synthesis prompt run locally
        self.info("  🔍 生成最終辯證結論...")
        synthesis_prompt = (
            "請閱讀以下師生辯證紀錄，並生成一份「盲點分析報告」：\n"
            "1. 列出學生最初理解中的 3 個核心盲點\n"
            "2. 說明每個盲點如何在辯證過程中被糾正\n"
            "3. 給出 1 個「最重要的深層知識點」，這是學生通過辯證才真正理解的\n\n"
            f"【辯證紀錄】\n{''.join(debate_log)}"
        )
        synthesis = self._llm.generate(model=_STUDENT_MODEL, prompt=synthesis_prompt)
        debate_log.append(f"\n## 🔍 盲點分析報告\n\n{synthesis}\n")

        # Write archive
        with open(archive_path, "w", encoding="utf-8") as f:
            f.write("\n".join(debate_log))

        self.info(f"  💾 辯證歸檔完成: {archive_path}")
        return archive_path

    # ------------------------------------------------------------------ #
    #  Phase Entry Point                                                   #
    # ------------------------------------------------------------------ #

    def run(self, force: bool = False, **kwargs) -> None:
        input_dir = self.phase_dirs["input"]
        output_dir = self.phase_dirs["output"]
        os.makedirs(output_dir, exist_ok=True)

        processed = 0
        for root, _, files in os.walk(input_dir):
            for fname in sorted(files):
                if not fname.endswith(".md"):
                    continue

                note_path = os.path.join(root, fname)
                state_key = os.path.relpath(note_path, input_dir)

                if not force and self.state_manager.is_complete(self.phase_key, state_key):
                    self.info(f"⏭️  已完成，跳過: {fname}")
                    continue

                self.info(f"\n📂 處理筆記: {fname}")
                with open(note_path, encoding="utf-8") as f:
                    note_content = f.read()

                if len(note_content.strip()) < 100:
                    self.warning(f"  ⚠️  筆記內容過短，跳過: {fname}")
                    continue

                try:
                    archive_path = asyncio.run(self._run_debate(note_path, note_content))

                    # Write a result pointer for Phase 2
                    out_path = os.path.join(output_dir, fname.replace(".md", "_debate.json"))
                    import json

                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(
                            {
                                "source_note": note_path,
                                "debate_archive": archive_path,
                            },
                            f,
                            ensure_ascii=False,
                            indent=2,
                        )

                    self.state_manager.mark_complete(self.phase_key, state_key)
                    processed += 1

                except Exception as exc:
                    self.error(f"  ❌ 辯證失敗: {exc}")

        self.info(f"\n✅ Phase 1 完成，共處理 {processed} 篇筆記。")
        self.state_manager.sync_physical_files()
