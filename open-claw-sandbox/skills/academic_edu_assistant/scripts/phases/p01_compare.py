import os
import sys

# P0-2: Guard against missing ChromaDB — skill should degrade gracefully
try:
    import chromadb as _chromadb

    CHROMADB_AVAILABLE = True
except ImportError:
    _chromadb = None  # type: ignore[assignment]
    CHROMADB_AVAILABLE = False

import requests

# Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import AtomicWriter, PipelineBase


class Phase1Compare(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="p1", phase_name="RAG 交叉比對", skill_name="academic_edu_assistant"
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

        # P0-2: Fail gracefully when ChromaDB is not installed
        if not CHROMADB_AVAILABLE:
            self.error(
                "\u274c ChromaDB \u672a\u5b89\u88dd (pip install chromadb) \u2014 RAG \u6bd4\u5c0d\u7121\u6cd5\u904b\u884c\u3002"
            )
            return

        # P0-2: Read ChromaDB path from config.yaml (vector_db.path) — remove cross-skill hardcode
        chroma_cfg = self.config_manager.get_section("vector_db") or {}
        db_path = chroma_cfg.get(
            "path",
            os.path.abspath(
                os.path.join(self.base_dir, "..", "telegram_kb_agent", "state", "chroma_db")
            ),
        )
        if not os.path.exists(db_path):
            self.error(
                "\u274c \u627e\u4e0d\u5230 ChromaDB \u5411\u91cf\u5eab\uff0c\u8acb\u5148\u57f7\u884c telegram_kb_agent \u7684 indexer.py\u3002"
            )
            return

        client = _chromadb.PersistentClient(path=db_path)
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

        prompt_tpl = self.get_prompt("Phase 1: RAG 交叉比對")
        if not prompt_tpl:
            self.error("❌ 找不到 prompt 指令，請確認 prompt.md 存在")
            return

        prompt = f"""{prompt_tpl}

【參考資料開始】
{context_str}
【參考資料結束】

使用者查詢字串：{query}

請以繁體中文撰寫結構嚴謹的比較報告：
"""
        model_name = self.config_manager.get_nested("models", "default") or "qwen3:8b"

        pbar, stop_tick, t = self.create_spinner(f"LLM 分析與生成報告中 ({model_name})...")
        try:
            response = self.llm.generate(model=model_name, prompt=prompt)
        except Exception as e:
            self.error(f"❌ 生成失敗: {e}")
            return
        finally:
            self.finish_spinner(pbar, stop_tick, t)
            # C Fix: unload model after use to release VRAM
            self.llm.unload_model(model_name, logger=self)

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
