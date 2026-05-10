import glob
import os
import sys

import chromadb
import requests

# Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core.utils.path_builder import PathBuilder


def get_config():
    import yaml

    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def chunk_text(text: str, chunk_size: int, overlap: int):
    """Simple sliding window chunker."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += chunk_size - overlap
    return chunks


def get_embedding(text: str, model: str, api_url: str):
    """Get embedding from Ollama."""
    url = f"{api_url}/embeddings"
    response = requests.post(url, json={"model": model, "prompt": text})
    if response.status_code == 200:
        return response.json().get("embedding")
    else:
        raise RuntimeError(f"Embedding failed: {response.text}")


def main():
    print("🚀 啟動 Knowledge Base Indexer...")

    cfg = get_config()
    rag_cfg = cfg.get("rag", {})
    chunk_size = rag_cfg.get("chunk_size", 1000)
    overlap = rag_cfg.get("chunk_overlap", 200)
    model = rag_cfg.get("embed_model", "nomic-embed-text")
    api_url = cfg.get("runtime", {}).get("ollama", {}).get("api_url", "http://127.0.0.1:11434/api")

    pb = PathBuilder(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
        "telegram_kb_agent",
    )
    pb.ensure_directories()

    wiki_dir = os.path.abspath(os.path.join(pb.base_dir, "..", "wiki"))
    db_path = os.path.join(pb.canonical_dirs["state"], "chroma_db")

    print(f"📦 初始化 ChromaDB 於: {db_path}")
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(name="wiki_knowledge")

    md_files = glob.glob(os.path.join(wiki_dir, "**", "*.md"), recursive=True)
    print(f"📄 找到 {len(md_files)} 個 Wiki 檔案，準備處理...")

    doc_ids = []
    embeddings = []
    documents = []
    metadatas = []

    for file_path in md_files:
        filename = os.path.basename(file_path)
        if filename == "INDEX.md":
            continue

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        chunks = chunk_text(content, chunk_size, overlap)

        for i, chunk in enumerate(chunks):
            doc_id = f"{filename}_chunk_{i}"

            try:
                emb = get_embedding(chunk, model, api_url)

                doc_ids.append(doc_id)
                embeddings.append(emb)
                documents.append(chunk)
                metadatas.append({"filename": filename, "chunk_index": i})

                print(f"  ✅ 已處理: {doc_id}")
            except Exception as e:
                print(f"  ❌ 處理失敗: {doc_id} - {e}")

    if doc_ids:
        print(f"💾 正在將 {len(doc_ids)} 筆向量資料存入 ChromaDB...")
        # Upsert automatically overwrites if the ID exists
        collection.upsert(
            ids=doc_ids, embeddings=embeddings, documents=documents, metadatas=metadatas
        )
        print("✅ 知識庫索引建立完成！")
    else:
        print("⚠️ 沒有任何資料被索引。")


if __name__ == "__main__":
    try:
        main()
        print("🏁 Pipeline 執行完畢。")
        try:
            import subprocess

            subprocess.run(
                [
                    "osascript",
                    "-e",
                    'display notification "Pipeline 執行完畢" with title "Open-Claw"',
                ],
                check=False,
            )
        except Exception:
            pass
    except KeyboardInterrupt:
        print("\n🛑 使用者手動中斷執行 (KeyboardInterrupt)")
        try:
            import subprocess

            subprocess.run(
                [
                    "osascript",
                    "-e",
                    'display notification "Execution Interrupted" with title "Open-Claw"',
                ],
                check=False,
            )
        except Exception:
            pass
        import sys

        sys.exit(130)
