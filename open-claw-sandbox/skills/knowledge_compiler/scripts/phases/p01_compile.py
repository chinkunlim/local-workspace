import datetime
import os
import re
import sys

# Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import AtomicWriter, PipelineBase

WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]")


class Phase1Compile(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="p1",
            phase_name="\u77e5\u8b58\u5eab\u7de8\u8b6f\u8207\u96d9\u5411\u9023\u7d50",
            skill_name="knowledge_compiler",
        )
        # P1-6: Resolve wiki_dir from config.yaml (output.wiki_dir) instead of hardcoded ../wiki
        output_cfg = self.config_manager.get_section("output") or {}
        default_wiki = os.path.abspath(os.path.join(self.base_dir, "..", "wiki"))
        self.wiki_dir = os.path.realpath(output_cfg.get("wiki_dir", default_wiki))
        os.makedirs(self.wiki_dir, exist_ok=True)

        self.model_name = self.config_manager.get_nested("models", "default") or "qwen2.5-coder:7b"

        # P1-6: Load system prompt from prompt.md (externalised — no more inline string literals)
        self._prompt_tpl = ""
        if os.path.exists(self.prompt_file):
            try:
                with open(self.prompt_file, encoding="utf-8") as f:
                    raw = f.read()
                # Extract section between "## Phase 1: Knowledge Compile" and next "---" or "##"
                import re as _re

                m = _re.search(
                    r"## Phase 1: Knowledge Compile.*?(?=\n## |\Z)",
                    raw,
                    _re.DOTALL,
                )
                self._prompt_tpl = m.group(0).strip() if m else raw.strip()
            except Exception as e:
                self.error(f"\u274c \u7121\u6cd5\u8b80\u53d6 prompt.md: {e}")
        if not self._prompt_tpl:
            # Fallback to minimal embedded prompt if file is missing
            self._prompt_tpl = (
                "\u4f60\u662f\u4e00\u500b\u5c08\u696d\u7684\u77e5\u8b58\u5eab\u67b6\u69cb\u5e2b\u3002"
                "\u8acb\u5c07\u4ee5\u4e0b\u5167\u5bb9\u91cd\u69cb\u70ba\u7d50\u69cb\u5316 Markdown\uff0c"
                "\u52a0\u5165 [[Obsidian \u96d9\u5411\u9023\u7d50]] \u8207\u5c0f\u6a19\u984c\u3002"
            )

        # We also create an INDEX.md if it doesn't exist
        self.index_file = os.path.join(self.wiki_dir, "INDEX.md")
        if not os.path.exists(self.index_file):
            AtomicWriter.write_text(
                self.index_file,
                "# \U0001f9e0 Knowledge Base Index\n\n\u81ea\u52d5\u7dad\u8b77\u7684\u77e5\u8b58\u5eab\u7d22\u5f15\u3002\n\n## \u6700\u65b0\u689d\u76ee\n",
            )

    def _update_index(self, title: str, filename: str):
        """Append a new entry to INDEX.md using AtomicWriter (P0-4: concurrent-safe)."""
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        entry = f"- [{date_str}] [[{title}]] (source: `{filename}`)\n"
        try:
            # Read existing content, then atomically rewrite with appended line
            existing = ""
            if os.path.exists(self.index_file):
                with open(self.index_file, encoding="utf-8") as f:
                    existing = f.read()
            AtomicWriter.write_text(self.index_file, existing + entry)
        except Exception as e:
            self.error(f"\u274c \u7121\u6cd5\u66f4\u65b0 INDEX.md: {e}")

    def _validate_wikilinks(self, text: str) -> tuple[str, int]:
        """Downgrade [[Dead Link]] to plain text if the target .md does not exist in wiki_dir.

        Prevents Obsidian from showing broken links after knowledge compilation.
        Returns (validated_text, count_downgraded).
        """
        downgraded = 0

        def _check(match: re.Match) -> str:
            nonlocal downgraded
            target = match.group(1).strip()
            # Resolve expected filename: try exact + .md
            target_path = os.path.join(self.wiki_dir, f"{target}.md")
            if not os.path.exists(target_path):
                # Also check if file exists without .md suffix (edge-case)
                alt_path = os.path.join(self.wiki_dir, target)
                if not os.path.exists(alt_path):
                    downgraded += 1
                    return target  # plain text — strip [[  ]]
            return match.group(0)  # keep as-is

        validated = WIKILINK_RE.sub(_check, text)
        if downgraded:
            self.info(f"\U0001f517 [WikiLink Guard] {downgraded} 個死連結已降級為純文字")
        return validated, downgraded

    def _process_file(self, idx: int, task: dict, total: int):
        subj = task["subject"]
        fname = task["filename"]
        in_path = os.path.join(self.base_dir, "input", subj, fname)

        if not os.path.exists(in_path):
            self.warning(f"⚠️ 找不到來源：{in_path}")
            return

        with open(in_path, encoding="utf-8") as f:
            content = f.read()

        self.info(
            f"\U0001f4dd [{idx}/{total}] \u7de8\u8b6f\u7b46\u8a18\uff1a[{subj}] {fname} ({len(content)} \u5b57\u5143)"
        )

        # P1-6: Use externalised prompt template (loaded from prompt.md in __init__)
        if "{INPUT_CONTENT}" in self._prompt_tpl:
            prompt = self._prompt_tpl.replace("{INPUT_CONTENT}", content)
        else:
            prompt = f"{self._prompt_tpl}\n\n<content>\n{content}\n</content>"

        pbar, stop_tick, t = self.create_spinner(f"LLM 編譯中 ({fname})")
        try:
            final_doc = self.llm.generate(model=self.model_name, prompt=prompt)

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

            # WikiLink Guard: downgrade dead [[Links]] before writing to vault
            final_doc, _ = self._validate_wikilinks(final_doc)

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

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.info("✨ 啟動 Phase 1：知識庫編譯與雙向連結")
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
