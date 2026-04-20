# -*- coding: utf-8 -*-
"""
core/knowledge_pusher.py — Open WebUI Knowledge Integration
============================================================
This script bridges Open Claw and Open WebUI. It takes a generated 
Markdown note (from note_generator) and pushes it to Open WebUI's
Knowledge Base API (or ChromaDB vector store) for retrieval-augmented
generation (RAG).
"""

import os
import sys
import json
import urllib.request
import urllib.error

_core_dir = os.path.dirname(os.path.abspath(__file__))
_workspace_root = os.environ.get("WORKSPACE_DIR", os.path.abspath(os.path.join(_core_dir, "..")))

class KnowledgePusher:
    def __init__(self):
        # Read API URL and Key from environment or defaults
        self.api_url = os.environ.get("WEBUI_API_URL", "http://127.0.0.1:8080/api/v1")
        self.api_key = os.environ.get("WEBUI_API_KEY", "")
        
    def push_to_knowledge_base(self, filepath: str, title: str = "", collection_name: str = "open-claw-notes") -> bool:
        """
        Pushes a Markdown file to the Open WebUI Knowledge API.
        """
        if not os.path.exists(filepath):
            print(f"❌ [Pusher] 檔案不存在: {filepath}")
            return False
            
        if not self.api_key:
            print("⚠️ [Pusher] 未設定 WEBUI_API_KEY，跳過知識庫推送。")
            return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            if not title:
                title = os.path.basename(filepath).replace(".md", "")
                
            payload = json.dumps({
                "collection_name": collection_name,
                "title": title,
                "content": content
            }).encode("utf-8")
            
            req = urllib.request.Request(
                f"{self.api_url}/knowledge/documents",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status in (200, 201):
                    print(f"✅ [Pusher] 成功將 {title} 推送至 Open WebUI 知識庫 ({collection_name})")
                    return True
                else:
                    print(f"⚠️ [Pusher] 推送失敗，狀態碼: {resp.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ [Pusher] 推送過程中發生錯誤: {e}")
            return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 knowledge_pusher.py <markdown_file_path> [collection_name]")
        sys.exit(1)
        
    filepath = sys.argv[1]
    collection = sys.argv[2] if len(sys.argv) > 2 else "open-claw-notes"
    
    pusher = KnowledgePusher()
    pusher.push_to_knowledge_base(filepath, collection_name=collection)
