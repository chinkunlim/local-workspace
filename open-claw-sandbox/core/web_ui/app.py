# -*- coding: utf-8 -*-
"""
core/web_ui/app.py — Open Claw Central Dashboard API
======================================================
"""
from __future__ import annotations

import os
import sys
import json
import subprocess
from flask import Flask, jsonify, request, render_template

# ── Bootstrap ────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.web_ui.execution_manager import ExecutionManager
from core.path_builder import PathBuilder
from core.llm_client import OllamaClient
import chromadb

app = Flask(__name__)
exec_mgr = ExecutionManager()

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
SKILLS_DIR = os.path.join(WORKSPACE_ROOT, "skills")
DATA_DIR = os.path.join(WORKSPACE_ROOT, "data")

def get_skills():
    if not os.path.isdir(SKILLS_DIR):
        return []
    return [d for d in os.listdir(SKILLS_DIR) if os.path.isdir(os.path.join(SKILLS_DIR, d)) and not d.startswith(".")]

def get_skill_state(skill: str):
    state_file = os.path.join(DATA_DIR, skill, "state", ".pipeline_state.json")
    if not os.path.exists(state_file):
        return {}
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def count_completed_files(state: dict, phase_key: str):
    count = 0
    for subj_files in state.values():
        for file_status in subj_files.values():
            if file_status.get(phase_key) == "✅":
                count += 1
    return count

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status", methods=["GET"])
def api_status():
    skills = get_skills()
    status = {"system": exec_mgr.get_status(), "skills": {}}
    
    for skill in skills:
        state = get_skill_state(skill)
        # Just return total files processed (count of unique files in state)
        total_files = sum(len(files) for files in state.values())
        status["skills"][skill] = {"total_files": total_files}
        
    return jsonify(status)

@app.route("/api/query", methods=["POST"])
def api_query():
    data = request.get_json(force=True) or {}
    query = data.get("query", "").strip()
    mode = data.get("mode", "rag") # 'rag' or 'compare'
    
    if not query:
        return jsonify({"success": False, "error": "Query is empty"}), 400
        
    if mode == "compare":
        # Launch academic-edu-assistant
        script_path = os.path.join(SKILLS_DIR, "academic-edu-assistant", "scripts", "run_all.py")
        cmd = ["python3", script_path, "--query", query]
        ok = exec_mgr.enqueue_task(f"Compare: {query}", cmd, cwd=WORKSPACE_ROOT)
        return jsonify({"success": ok, "message": "已排入背景比對佇列！"})
    
    # Mode RAG: direct synchronous query
    db_path = os.path.join(DATA_DIR, "telegram-kb-agent", "state", "chroma_db")
    if not os.path.exists(db_path):
        return jsonify({"success": False, "error": "找不到知識庫向量索引，請先建立。"}), 400
        
    try:
        # Quick RAG implementation for Web UI
        import requests
        url = "http://127.0.0.1:11434/api/embeddings"
        res = requests.post(url, json={"model": "nomic-embed-text", "prompt": query})
        query_emb = res.json().get("embedding")
        
        client = chromadb.PersistentClient(path=db_path)
        collection = client.get_collection(name="wiki_knowledge")
        results = collection.query(query_embeddings=[query_emb], n_results=3)
        
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        
        if not documents:
            return jsonify({"success": True, "answer": "知識庫中找不到相關資訊。"})
            
        context_str = "\n\n---\n\n".join([f"[來源: {m.get('filename')}]\n{d}" for d, m in zip(documents, metadatas)])
        prompt = f"請根據以下參考資料回答：\n\n{context_str}\n\n問題：{query}"
        
        ollama_client = OllamaClient(api_url="http://127.0.0.1:11434/api/generate")
        answer = ollama_client.generate(model="qwen2.5-coder:7b", prompt=prompt)
        
        return jsonify({"success": True, "answer": answer, "sources": metadatas})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/start", methods=["POST"])
def api_start():
    data = request.get_json(force=True) or {}
    skill = data.get("skill", "").strip()
    
    if not skill or skill not in get_skills():
        return jsonify({"success": False, "error": "Invalid skill"}), 400
        
    script_path = os.path.join(SKILLS_DIR, skill, "scripts", "run_all.py")
    if not os.path.exists(script_path):
        return jsonify({"success": False, "error": "Skill runner not found"}), 400
        
    cmd = ["python3", script_path]
    ok = exec_mgr.enqueue_task(f"{skill} Pipeline", cmd, cwd=WORKSPACE_ROOT)
    return jsonify({"success": ok})

if __name__ == "__main__":
    host = os.environ.get("DASHBOARD_HOST", "127.0.0.1")
    port = int(os.environ.get("DASHBOARD_PORT", "5001"))
    print(f"🌐 Open Claw Knowledge App → http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
