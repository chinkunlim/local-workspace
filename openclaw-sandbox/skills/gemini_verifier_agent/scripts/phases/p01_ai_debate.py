import asyncio
import json
import os

from core.ai.llm_client import OllamaClient
from core.orchestration.pipeline_base import PipelineBase as PhaseBase
from core.utils.atomic_writer import AtomicWriter
from core.utils.playwright_utils import get_persistent_context


class Phase1AIDebate(PhaseBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="p01_ai_debate",
            phase_name="AI-to-AI Debate and Verification",
            skill_name="gemini_verifier_agent",
        )
        self.llm = OllamaClient()

    async def _debate_gemini(self, claim: str, evidence: str) -> str | None:
        archive_dir = os.path.join(self.base_dir, "data", "gemini_verifier_agent", "archives")
        os.makedirs(archive_dir, exist_ok=True)

        async with get_persistent_context(headless=True) as context:
            page = await context.new_page()
            print("🤖 連線至 Gemini 進行查證...")
            try:
                await page.goto(
                    "https://gemini.google.com/app", wait_until="domcontentloaded", timeout=60000
                )

                # Wait for the chat input box (Gemini uses rich-textarea or contenteditable div)
                await page.wait_for_selector('div[contenteditable="true"]', timeout=30000)

                initial_prompt = (
                    f"請以學術標準驗證以下宣稱 (Claim): '{claim}'\n"
                    f"這是我們擷取到的文獻快照: {evidence}\n"
                    "請告訴我這份文獻是否支持該宣稱？有沒有矛盾之處？請引用文中的確切字句 (Exact Quote)。"
                )

                # Type into the input box
                await page.fill('div[contenteditable="true"]', initial_prompt)
                await page.keyboard.press("Enter")

                # Wait for response to generate (Gemini UI typically has a response container)
                # This is a heuristic: wait for the stop generating button to appear and disappear, or wait for text.
                print("⏳ 等待 Gemini 回覆...")
                await asyncio.sleep(15)  # Wait for network and generation

                # Extract the last response message
                response_elements = await page.query_selector_all("message-content")
                if response_elements:
                    last_response = await response_elements[-1].inner_text()
                else:
                    # Fallback to body extraction
                    last_response = await page.evaluate("document.body.innerText")

                # Debate Loop (Local LLM thinking about Gemini's response)
                debate_history = [
                    f"**Student (Local LLM)**: {initial_prompt}\n",
                    f"**Professor (Gemini)**: {last_response}\n",
                ]

                # Turn 2: Local LLM generates follow-up
                reflection_prompt = (
                    "You are a critical university student. Read Gemini's response:\n"
                    f"{last_response}\n\n"
                    "Does this fully answer the claim? Generate a short follow-up question to ask Gemini to deepen the analysis or clarify a doubt. If it is perfect, output 'NO_QUESTIONS'."
                )
                # primary: qwen3:14b; fallback: qwen3:8b (via config.yaml)
                followup = self.llm.generate(model="qwen3:14b", prompt=reflection_prompt)

                if "NO_QUESTIONS" not in followup:
                    print(f"🤔 本地模型追問: {followup}")
                    await page.fill('div[contenteditable="true"]', followup)
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(15)

                    response_elements = await page.query_selector_all("message-content")
                    if response_elements:
                        second_response = await response_elements[-1].inner_text()
                        debate_history.append(f"**Student (Local LLM)**: {followup}\n")
                        debate_history.append(f"**Professor (Gemini)**: {second_response}\n")
                        last_response = second_response

                # Archive the debate
                archive_path = os.path.join(
                    archive_dir, f"debate_{claim[:15].replace(' ', '_')}.md"
                )
                debate_text = "\n\n".join(debate_history)
                AtomicWriter.write_text(archive_path, debate_text)

                print(f"✅ AI 辯證階段完成，輸出至: {archive_path}")

            except Exception as exc:
                self.warning(f"⚠️  Playwright 流程失敗: {exc}")

        return None

        self.state_manager.sync_physical_files()
