import datetime
import os
import re
import sys

# Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import AtomicWriter, PipelineBase


class Phase1Compile(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="p1", phase_name="知識庫編譯與雙向連結", skill_name="knowledge-compiler"
        )
        self.wiki_dir = os.path.abspath(os.path.join(self.base_dir, "..", "wiki"))
        os.makedirs(self.wiki_dir, exist_ok=True)

        # We also create an INDEX.md if it doesn't exist
        self.index_file = os.path.join(self.wiki_dir, "INDEX.md")
        if not os.path.exists(self.index_file):
            AtomicWriter.write_text(
                self.index_file,
                "# 🧠 Knowledge Base Index\n\n自動維護的知識庫索引。\n\n## 最新條目\n",
            )

    def _update_index(self, title: str, filename: str):
        """Append to INDEX.md"""
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        entry = f"- [{date_str}] [[{title}]] (source: `{filename}`)\n"
        try:
            with open(self.index_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            self.error(f"❌ 無法更新 INDEX.md: {e}")

    def _process_file(self, idx: int, task: dict, total: int):
        subj = task["subject"]
        fname = task["filename"]
        in_path = os.path.join(self.base_dir, "input", subj, fname)

        if not os.path.exists(in_path):
            self.warning(f"⚠️ 找不到來源：{in_path}")
            return

        with open(in_path, encoding="utf-8") as f:
            content = f.read()

        self.info(f"📝 [{idx}/{total}] 編譯筆記：[{subj}] {fname} ({len(content)} 字元)")

        # Prepare prompt
        system_prompt = """
你是一個專業的知識庫架構師與分析師。
請閱讀以下的原始筆記或文件內容，並根據以下規則進行重構：

1. 總結與提煉：不破壞原意，將內容重構為結構化的 Markdown。
2. 結構要求：
   # [請根據內容自訂一個精準的標題]
   > [一句話核心摘要]
   ## 核心概念
   [詳細條列或段落說明]
3. 雙向連結標註 (Graphify)：
   - 識別文章中的「重要概念、專有名詞、理論模型」。
   - 將其用 Obsidian 雙向連結格式包覆，例如：[[認知心理學]]、[[Python]]。
   - 同一個概念在文章中只需標註第一次出現的地方。
4. 領域關聯：在文章底部加上「## 延伸連結」，列出關聯的領域標籤（例如 #Psychology, #Programming, #AI, #Teaching）以及 2~3 個強相關概念的雙向連結。
"""

        prompt = f"{system_prompt}\n\n<content>\n{content}\n</content>"

        pbar, stop_tick, t = self.create_spinner(f"LLM 編譯中 ({fname})")
        try:
            # We use Qwen2.5-Coder:7b or similar default model
            final_doc = self.llm.generate(model="qwen2.5-coder:7b", prompt=prompt)

            # Extract title to name the file in wiki/
            title_match = re.search(r"^#\s+(.+)$", final_doc, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()
                safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
            else:
                title = os.path.splitext(fname)[0]
                safe_title = title

            out_filename = f"{safe_title}.md"
            out_path = os.path.join(self.wiki_dir, out_filename)

            AtomicWriter.write_text(out_path, final_doc)

            # Update INDEX.md
            self._update_index(title, out_filename)

            # Mark as completed in state manager
            self.state_manager.update_task(subj, fname, self.phase_key, char_count=len(final_doc))
            self.info(f"✅ [{idx}/{total}] 編譯完成：{out_path}")

        except Exception as e:
            self.error(f"❌ 編譯失敗 {fname}: {e}")
        finally:
            self.finish_spinner(pbar, stop_tick, t)
            self.llm.unload_model("qwen2.5-coder:7b", logger=self)

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.info("✨ 啟動 Phase 1：知識庫編譯與雙向連結")
        self.process_tasks(
            self._process_file,
            force=force,
            subject_filter=subject,
            file_filter=file_filter,
            single_mode=single_mode,
            resume_from=resume_from,
        )
