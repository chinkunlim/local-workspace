import os
import sys

import chromadb
import requests

# Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import AtomicWriter, PipelineBase

# A-7 Fix: promote hardcoded model name to a named constant
_ANALYSIS_MODEL = "qwen2.5-coder:7b"


class Phase1Compare(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="p1", phase_name="RAG 交叉比對", skill_name="academic-edu-assistant"
        )

    def get_embedding(self, text: str, model: str, api_url: str):
        url = f"{api_url}/embeddings"
        try:
            response = requests.post(url, json={"model": model, "prompt": text})
            if response.status_code == 200:
                return response.json().get("embedding")
            else:
                raise RuntimeError(f"Embedding failed: {response.text}")
        except requests.exceptions.ConnectionError:
            self.warning("⚠️ Ollama 連線失敗，使用 MOCK 向量")
            return [0.1] * 768

    def run(
        self,
        force=False,
        subject=None,
        file_filter=None,
        single_mode=False,
        query=None,
        resume_from=None,
    ):
        self.info("✨ 啟動 Phase 1：RAG 交叉比對")

        if not query:
            self.info("⚠️ 沒有提供 --query 參數，跳過 RAG 交叉比對。")
            return

        self.info(f"🔍 查詢字串: {query}")

        # Connect to ChromaDB from telegram-kb-agent
        db_path = os.path.abspath(
            os.path.join(self.base_dir, "..", "telegram-kb-agent", "state", "chroma_db")
        )
        if not os.path.exists(db_path):
            self.error("❌ 找不到 ChromaDB 向量庫，請先執行 telegram-kb-agent 的 indexer.py。")
            return

        client = chromadb.PersistentClient(path=db_path)
        collection = client.get_collection(name="wiki_knowledge")

        ollama_api_url = "http://127.0.0.1:11434/api"
        embed_model = "nomic-embed-text"

        pbar, stop_tick, t = self.create_spinner("檢索向量庫...")
        try:
            query_emb = self.get_embedding(query, embed_model, ollama_api_url)
            results = collection.query(query_embeddings=[query_emb], n_results=10)
        finally:
            self.finish_spinner(pbar, stop_tick, t)

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        if not documents:
            self.warning("❌ 知識庫中找不到相關資訊可以比對。")
            return

        context_str = "\n\n---\n\n".join(
            [f"[來源: {m.get('filename')}]\n{d}" for d, m in zip(documents, metadatas)]
        )

        prompt = f"""
你是一個嚴謹的學術研究助理。請根據以下「參考資料」，針對使用者的「查詢字串」進行深度的交叉比對與綜合分析。
你必須：
1. 提取出核心的對立或關聯觀點。
2. 找出文獻之間的「共同點」與「相異點」。
3. 最後必須輸出一個 Markdown 比較表格總結差異。

【參考資料開始】
{context_str}
【參考資料結束】

使用者查詢字串：{query}

請以繁體中文撰寫結構嚴謹的比較報告：
"""
        pbar, stop_tick, t = self.create_spinner("LLM 分析與生成報告中...")
        try:
            response = self.llm.generate(model=_ANALYSIS_MODEL, prompt=prompt)
        except Exception as e:
            self.error(f"❌ 生成失敗: {e}")
            return
        finally:
            self.finish_spinner(pbar, stop_tick, t)
            # C Fix: unload model after use to release VRAM
            self.llm.unload_model(_ANALYSIS_MODEL, logger=self)

        # Write to output/01_comparison/<query>.md
        safe_name = (
            "".join(c for c in query if c.isalnum() or c in (" ", "_", "-"))
            .strip()
            .replace(" ", "_")
        )
        out_dir = os.path.join(self.base_dir, "output", "01_comparison")
        os.makedirs(out_dir, exist_ok=True)

        out_path = os.path.join(out_dir, f"{safe_name}.md")
        AtomicWriter.write_text(out_path, f"# {query}\n\n{response}\n")

        self.info(f"✅ 比較報告已儲存至: {out_path}")

        # We manually update state for this generated file so Phase 2 can pick it up
        with self.state_manager._lock:
            if "Queries" not in self.state_manager.state:
                self.state_manager.state["Queries"] = {}
            if f"{safe_name}.md" not in self.state_manager.state["Queries"]:
                self.state_manager.state["Queries"][f"{safe_name}.md"] = dict.fromkeys(
                    self.state_manager.PHASES, "⏳"
                )
            self.state_manager._save_state()

        self.state_manager.update_task("Queries", f"{safe_name}.md", self.phase_key)
