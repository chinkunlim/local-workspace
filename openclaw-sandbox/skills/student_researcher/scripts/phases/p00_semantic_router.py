import json
import os
import re
import sys

# Core Bootstrap
from core import AtomicWriter, PipelineBase


class Phase0SemanticRouter(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="p0",
            phase_name="語意尋根與孵化分配 (Semantic Router)",
            skill_name="student_researcher",
        )
        self.model_name = self.config_manager.get_nested("models", "default") or "qwen3:8b"
        self.semantic_ctx_path = os.path.join(self.base_dir, "state", "semantic_context.json")
        self._context_cache = {}
        if os.path.exists(self.semantic_ctx_path):
            try:
                with open(self.semantic_ctx_path, encoding="utf-8") as f:
                    self._context_cache = json.load(f)
            except Exception:
                pass

    def _save_context(self):
        AtomicWriter.write_json(self.semantic_ctx_path, self._context_cache)

    def _get_embedding(self, text: str) -> list[float]:
        import requests

        api_url = (
            self.config_manager.get_nested("runtime", "ollama", "api_url")
            or "http://127.0.0.1:11434/api"
        )
        url = f"{api_url}/embeddings"
        try:
            resp = requests.post(
                url, json={"model": "nomic-embed-text", "prompt": text}, timeout=10
            )
            if resp.ok:
                return resp.json().get("embedding", [])
        except Exception as e:
            self.warning(f"  ⚠️ 無法取得 Embedding: {e}")
        return []

    def _process_file(self, idx: int, task: dict, total: int):
        subj = task["subject"]
        fname = task["filename"]

        # Only process files that were assigned to 'inbox' or 'Default' or lack a specific tag,
        # but in our architecture, inbox_daemon already moves files.
        # However, for 'Ollama_' or 'Gemini_' prefix files that don't have a clear subject,
        # they might be placed in a default folder.
        # If it already has a specific subject (not Incubator and not Default), we might still want to find links,
        # but Incubator logic applies when it's totally unknown.
        # Let's run semantic routing for ALL files in student_researcher to enrich them!

        in_path = os.path.join(self.base_dir, "input", subj, fname)
        if not os.path.exists(in_path):
            self.warning(f"⚠️ 找不到來源：{in_path}")
            return

        # Check if already processed
        if f"{subj}/{fname}" in self._context_cache:
            self.info(f"⏭️ [{idx}/{total}] 已語意比對過：{fname}")
            return

        with open(in_path, encoding="utf-8") as f:
            content = f.read()

        self.info(f"🔍 [{idx}/{total}] 語意尋根：[{subj}] {fname}")

        # Step 1: LLM summary
        pbar, stop_tick, t = self.create_spinner(f"LLM 摘要與分類 ({fname})")
        summary_prompt = (
            "請用繁體中文為以下對話或筆記寫一段 100 字以內的摘要。\n"
            "這段摘要將用來進行向量比對，請抓出核心概念、專業術語與領域。\n\n"
            f"<content>\n{content[:2000]}\n</content>"
        )
        try:
            summary = self.llm.generate(
                model=self.model_name, prompt=summary_prompt, options={"temperature": 0.0}
            )
        except Exception as e:
            self.error(f"❌ 摘要失敗: {e}")
            summary = content[:500]
        self.finish_spinner(pbar, stop_tick, t)

        # Step 2: Vector Search
        related_files = []
        try:
            import chromadb

            db_path = os.path.join(
                self.workspace_root, "skills", "telegram_kb_agent", "state", "chroma_db"
            )
            if os.path.exists(db_path):
                client = chromadb.PersistentClient(path=db_path)
                collection = client.get_collection("wiki_knowledge")
                emb = self._get_embedding(summary)
                if emb:
                    res = collection.query(query_embeddings=[emb], n_results=3)  # type: ignore[arg-type]
                    metadatas = res.get("metadatas") or [[]]
                    distances = res.get("distances") or [[]]
                    for m, dist in zip(metadatas[0], distances[0]):  # type: ignore[index, union-attr]
                        if dist < 0.3:  # High similarity threshold
                            related_files.append(str(m.get("filename", "")))
        except ImportError:
            self.warning("⚠️ chromadb 未安裝，跳過向量比對")
        except Exception as e:
            self.warning(f"⚠️ 向量比對發生錯誤: {e}")

        # Step 3: Determine Incubator or Link
        new_tags = []
        is_orphan = len(related_files) == 0 and subj in ["Default", "inbox", ""]

        if is_orphan:
            self.info("💡 發現孤兒點子！啟動孵化器機制 (Incubator)...")
            tag_prompt = (
                "這是一段沒有明確學科歸屬的新靈感。請根據內容，提出 3 個廣泛的本體論 Hashtag（例如 #未來趨勢, #量子計算, #經濟）。\n"
                "請只輸出這 3 個 Hashtag，以逗號分隔，不要有其他文字。\n\n"
                f"<content>\n{summary}\n</content>"
            )
            try:
                tag_res = self.llm.generate(
                    model=self.model_name, prompt=tag_prompt, options={"temperature": 0.0}
                )
                # Extract tags matching #xxx
                new_tags = re.findall(r"#[^\s,]+", tag_res)
                if not new_tags:
                    new_tags = [tag.strip() for tag in tag_res.split(",") if tag.strip()]
            except Exception:
                new_tags = ["#孵化中"]
        else:
            if related_files:
                self.info(f"🔗 找到 {len(related_files)} 個高度相關的現有知識點。")

        # Save to context
        self._context_cache[f"{subj}/{fname}"] = {
            "summary": summary,
            "related_files": related_files,
            "new_tags": new_tags,
            "is_orphan": is_orphan,
        }
        self._save_context()

        # Update task state
        self.state_manager.update_task(subj, fname, self.phase_key)

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.info("✨ 啟動 Phase 0：語意尋根與孵化分配 (Semantic Router)")
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


if __name__ == "__main__":
    Phase0SemanticRouter().run(force=True)
