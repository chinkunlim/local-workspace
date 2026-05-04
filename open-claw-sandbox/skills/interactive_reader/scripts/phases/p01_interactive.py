import os
import re
import sys

# Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import AtomicWriter, PipelineBase


class Phase1Interactive(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p1", phase_name="互動標籤處理", skill_name="interactive_reader")
        self.wiki_dir = os.path.abspath(os.path.join(self.base_dir, "..", "wiki"))
        self.model_name = self.config_manager.get_nested("models", "default") or "qwen3:8b"

    def _process_file(self, idx: int, task: dict, total: int):
        fname = task["filename"]
        in_path = os.path.join(self.wiki_dir, fname)

        if not os.path.exists(in_path):
            self.warning(f"⚠️ 找不到來源：{in_path}")
            return

        with open(in_path, encoding="utf-8") as f:
            content = f.read()

        # Find all > [AI: command] tags
        # We use a non-greedy match. Also allow optional spaces.
        pattern = re.compile(r"^> \[AI:\s*(.+?)\]\s*$", re.MULTILINE)
        matches = list(pattern.finditer(content))

        if not matches:
            # Mark as completed if no tags found
            self.state_manager.update_task("Wiki", fname, self.phase_key)
            return

        self.info(f"📝 [{idx}/{total}] 發現 {len(matches)} 個互動標籤：{fname}")

        modified_content = content

        # Process from back to front to avoid messing up indices
        for m in reversed(matches):
            if self.stop_requested:
                break

            instruction = m.group(1).strip()
            self.info(f"  🔍 處理標籤: {instruction}")

            # Extract Context Window (1000 chars before and after)
            start_idx = max(0, m.start() - 1000)
            end_idx = min(len(content), m.end() + 1000)
            context = content[start_idx:end_idx]

            system_prompt = f"""
你是一個 Obsidian 筆記內的 AI 協作助理。
使用者在閱讀筆記時，針對特定段落留下了指令。
請根據以下提供的「上下文」來執行使用者的指令。

【上下文內容開始】
...
{context}
...
【上下文內容結束】

規則：
1. 直接回答或執行指令，不需要打招呼或說「好的」。
2. 如果使用者要求畫「心智圖」，請嚴格輸出包含 `mindmap` 宣告的 Mermaid 語法區塊。
3. 如果使用者要求「解釋」或「問答」，請簡明扼要地回答。
4. 你的輸出將會直接被附加在原筆記中。
"""
            pbar, stop_tick, t = self.create_spinner(f"AI 思考中 ({instruction[:10]}...)")
            try:
                response = self.llm.generate(
                    model=self.model_name, prompt=f"{system_prompt}\n\n使用者指令：{instruction}"
                )

                # Format the replacement
                # Replace > [AI: ...] with > [AI-DONE: ...]
                # And append the response as blockquotes
                formatted_response = "\n".join(
                    [f"> {line}" if line.strip() else ">" for line in response.split("\n")]
                )

                replacement = (
                    f"> [AI-DONE: {instruction}]\n>\n> 🤖 **AI 回應：**\n{formatted_response}\n"
                )

                # Replace exactly this match
                modified_content = (
                    modified_content[: m.start()] + replacement + modified_content[m.end() :]
                )

            except Exception as e:
                self.error(f"❌ 標籤處理失敗 [{instruction}]: {e}")
            finally:
                self.finish_spinner(pbar, stop_tick, t)

        if modified_content != content:
            AtomicWriter.write_text(in_path, modified_content)
            self.info(f"✅ [{idx}/{total}] 回寫完成：{fname}")

        # Update status
        self.state_manager.update_task("Wiki", fname, self.phase_key)

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.info("✨ 啟動 Phase 1：互動閱讀與原地協作")
        try:
            self.process_tasks(
                self._process_file,
                force=force,
                subject_filter=subject,
                file_filter=file_filter,
                single_mode=single_mode,
                resume_from=resume_from,
            )
        finally:
            self.llm.unload_model(self.model_name, logger=self)
