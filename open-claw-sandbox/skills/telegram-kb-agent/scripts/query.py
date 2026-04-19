# -*- coding: utf-8 -*-
import os
import sys
import argparse
import requests
import chromadb

# Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.bootstrap import ensure_core_path as _bootstrap
_bootstrap(__file__)

from core.llm_client import OllamaClient

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

def get_embedding(text: str, model: str, api_url: str):
    url = f"{api_url}/embeddings"
    response = requests.post(url, json={"model": model, "prompt": text})
    if response.status_code == 200:
        return response.json().get("embedding")
    else:
        raise RuntimeError(f"Embedding failed: {response.text}")

def main():
    parser = argparse.ArgumentParser(description="Telegram KB Agent RAG Query")
    parser.add_argument("--query", type=str, required=True, help="User's question")
    args = parser.parse_args()
    
    query = args.query
    
    ollama_api_url = "http://127.0.0.1:11434/api"
    ollama_client = OllamaClient(api_url=f"{ollama_api_url}/generate")
    embed_model = "nomic-embed-text"
    generate_model = "qwen2.5-coder:7b"
    
    db_path = os.path.join(WORKSPACE_ROOT, "data", "telegram-kb-agent", "state", "chroma_db")
    if not os.path.exists(db_path):
        print("❌ 找不到向量庫，請先執行 indexer.py。")
        sys.exit(1)
        
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_collection(name="wiki_knowledge")
    
    try:
        query_emb = get_embedding(query, embed_model, ollama_api_url)
        results = collection.query(query_embeddings=[query_emb], n_results=3)
        
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        
        if not documents:
            print("❌ 知識庫中找不到相關資訊。")
            sys.exit(0)
            
        context_str = "\n\n---\n\n".join([f"[來源: {m.get('filename')}]\n{d}" for d, m in zip(documents, metadatas)])
        prompt = f"你是一個個人的 AI 知識庫助理。請根據以下「參考資料」回答使用者的問題。\n\n【參考資料開始】\n{context_str}\n【參考資料結束】\n\n使用者問題：{query}"
        
        answer = ollama_client.generate(model=generate_model, prompt=prompt)
        print(answer)
        
    except requests.exceptions.ConnectionError:
        print("⚠️ 無法連線至 Ollama 模型服務。")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
