"""
core/hybrid_retriever.py — Hybrid RAG Retriever (P3-3)
======================================================
Vector top-K ∪ GraphStore 1-hop expansion → LLM rerank → ordered context.

Config (config.yaml):
    hybrid_retriever:
      vector_top_k: 10
      graph_max_hops: 1
      rerank: true
      rerank_model: "qwen3:8b"
      rerank_top_n: 5
    vector_db:
      path: "skills/telegram_kb_agent/state/chroma_db"

Requirements:
    pip install networkx chromadb
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional

_logger = logging.getLogger("OpenClaw.HybridRetriever")


class HybridRetriever:
    """Vector top-K ∪ Graph 1-hop → optional LLM rerank."""

    def __init__(self, workspace_root: str, skill_name: str = "telegram_kb_agent"):
        self.workspace_root = workspace_root
        self.skill_name = skill_name
        self._chroma_client: Any = None
        self._collection: Any = None
        self._graph_store: Any = None
        self._llm: Any = None

        import sys

        sys.path.insert(0, workspace_root)
        from core.config.config_manager import ConfigManager  # type: ignore[import]

        cfg = ConfigManager(workspace_root, skill_name)
        hr = cfg.get_section("hybrid_retriever") or {}
        self._vector_top_k: int = hr.get("vector_top_k", 10)
        self._graph_max_hops: int = hr.get("graph_max_hops", 1)
        self._rerank: bool = hr.get("rerank", True)
        self._rerank_model: str = hr.get("rerank_model", "qwen3:8b")
        self._rerank_top_n: int = hr.get("rerank_top_n", 5)

        vec = cfg.get_section("vector_db") or {}
        self._vector_db_path: str = vec.get(
            "path",
            os.path.join(workspace_root, "skills", "telegram_kb_agent", "state", "chroma_db"),
        )
        rt = (cfg.get_section("runtime") or {}).get("ollama", {})
        self._ollama_url: str = rt.get("api_url", "http://127.0.0.1:11434/api")
        self._embed_model: str = (cfg.get_section("models") or {}).get("embed", "nomic-embed-text")

    # ── Lazy helpers ──────────────────────────────────────────────────────

    def _get_chroma(self):
        if self._collection is not None:
            return self._collection
        try:
            import chromadb  # type: ignore[import]
        except ImportError as exc:
            raise ImportError("pip install chromadb") from exc
        if not os.path.exists(self._vector_db_path):
            raise FileNotFoundError(f"ChromaDB not found at {self._vector_db_path}")
        self._chroma_client = chromadb.PersistentClient(path=self._vector_db_path)
        self._collection = self._chroma_client.get_collection("wiki_knowledge")
        return self._collection

    def _get_graph(self):
        if self._graph_store is None:
            from core.ai.graph_store import get_graph_store  # type: ignore[import]

            self._graph_store = get_graph_store(self.workspace_root, self.skill_name)
        return self._graph_store

    def _get_llm(self):
        if self._llm is None:
            from core.ai.llm_client import OllamaClient  # type: ignore[import]

            self._llm = OllamaClient(api_url=self._ollama_url)
        return self._llm

    def _embed(self, text: str) -> List[float]:
        import requests

        # Build embeddings URL: strip /generate suffix, append /embeddings
        base_url = self._ollama_url
        for _sfx in ("/generate", "/api/generate"):
            if base_url.endswith(_sfx):
                base_url = base_url[: -len(_sfx)]
                break
        embed_url = base_url.rstrip("/") + "/embeddings"

        resp = requests.post(
            embed_url,
            json={"model": self._embed_model, "prompt": text},
            timeout=30,
        )
        return resp.json().get("embedding", [0.1] * 768) if resp.ok else [0.1] * 768

    # ── Public API ────────────────────────────────────────────────────────

    def query(
        self,
        question: str,
        top_n: Optional[int] = None,
        skip_graph: bool = False,
        skip_rerank: bool = False,
    ) -> List[Dict[str, Any]]:
        """Hybrid retrieval: vector + graph + optional rerank.

        Returns:
            List of dicts with keys: text, source, score, origin (vector|graph).
        """
        top_n = top_n or self._rerank_top_n
        passages: List[Dict[str, Any]] = []

        # Step 1: Vector retrieval
        try:
            col = self._get_chroma()
            emb = self._embed(question)
            res = col.query(query_embeddings=[emb], n_results=self._vector_top_k)
            for doc, meta, dist in zip(
                res.get("documents", [[]])[0],
                res.get("metadatas", [[]])[0],
                res.get("distances", [[]])[0],
            ):
                passages.append(
                    {
                        "text": doc,
                        "source": meta.get("filename", "unknown"),
                        "score": 1.0 / (1.0 + dist),
                        "origin": "vector",
                    }
                )
            _logger.info("[HybridRetriever] Vector: %d passages.", len(passages))
        except Exception as exc:
            _logger.warning("[HybridRetriever] Vector search failed: %s", exc)

        # Step 2: Graph expansion
        if not skip_graph:
            try:
                graph = self._get_graph()
                candidates = re.findall(r"[\u4e00-\u9fff]{2,10}|[A-Z][a-zA-Z]{2,}", question)
                seen: set = set()
                for entity in candidates:
                    if not graph.entity_exists(entity):
                        continue
                    for nbr in graph.get_neighbours(entity, self._graph_max_hops):
                        name = nbr["name"]
                        if name not in seen:
                            seen.add(name)
                            passages.append(
                                {
                                    "text": f"[圖譜] {entity} {nbr['relation']} {name}",
                                    "source": "knowledge_graph",
                                    "score": 0.6,
                                    "origin": "graph",
                                }
                            )
                _logger.info("[HybridRetriever] Graph: %d passages.", len(seen))
            except Exception as exc:
                _logger.warning("[HybridRetriever] Graph expansion failed: %s", exc)

        # Deduplicate
        seen_texts: set = set()
        deduped = []
        for p in sorted(passages, key=lambda x: x["score"], reverse=True):
            key = p["text"][:120]
            if key not in seen_texts:
                seen_texts.add(key)
                deduped.append(p)

        # Step 3: LLM rerank
        if self._rerank and not skip_rerank and len(deduped) > top_n:
            try:
                deduped = self._llm_rerank(question, deduped, top_n)
            except Exception as exc:
                _logger.warning("[HybridRetriever] Rerank failed: %s", exc)
                deduped = deduped[:top_n]
        else:
            deduped = deduped[:top_n]

        return deduped

    def _llm_rerank(
        self, question: str, passages: List[Dict[str, Any]], top_n: int
    ) -> List[Dict[str, Any]]:
        numbered = "\n\n".join(f"[{i + 1}] {p['text'][:300]}" for i, p in enumerate(passages))
        prompt = (
            f"問題：{question}\n\n候選段落：\n{numbered}\n\n"
            f"選出最相關的 {top_n} 段，輸出逗號分隔序號，例如：3,1,5。只輸出序號。"
        )
        raw = self._get_llm().generate(model=self._rerank_model, prompt=prompt).strip()
        indices = [int(x) - 1 for x in re.findall(r"\d+", raw) if 0 < int(x) <= len(passages)]
        reranked = [passages[i] for i in indices]
        mentioned = set(indices)
        for i, p in enumerate(passages):
            if len(reranked) >= top_n:
                break
            if i not in mentioned:
                reranked.append(p)
        return reranked[:top_n]

    def format_context(self, passages: List[Dict[str, Any]]) -> str:
        """Format passages as an LLM context block."""
        parts = []
        for i, p in enumerate(passages, 1):
            tag = "📊 圖譜" if p["origin"] == "graph" else "📄 向量"
            parts.append(f"[{i}] {tag} (來源: {p['source']})\n{p['text']}")
        return "\n\n---\n\n".join(parts)
