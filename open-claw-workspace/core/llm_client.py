import requests
import time
from typing import Dict, Any, Optional

class OllamaClient:
    def __init__(self, api_url: str = "http://127.0.0.1:11434/api/generate", timeout: int = 600, retries: int = 3):
        self.api_url = api_url
        self.timeout = timeout
        self.retries = retries

    def generate(self, model: str, prompt: str, options: Optional[Dict[str, Any]] = None, logger=None) -> str:
        """Call Ollama generation endpoint with error retries."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if options:
            payload["options"] = options
            
        for attempt in range(self.retries):
            try:
                res = requests.post(self.api_url, json=payload, timeout=self.timeout)
                res.raise_for_status()
                response_text = res.json().get('response', '')
                
                if not response_text or not response_text.strip():
                    raise ValueError(f"Ollama 回傳空內容（可能原因：num_predict 耐盡、網路超時、模型載入失敗）")
                return response_text
            except requests.exceptions.RequestException as e:
                if attempt < self.retries - 1:
                    if logger:
                        logger.warning(f"Ollama 請求失敗 ({e})，正在進行第 {attempt + 2} 次重試...")
                    time.sleep(5)
                else:
                    if logger:
                        logger.error(f"Ollama 請求徹底失敗: {e}")
                    raise

    def unload_model(self, model: str, logger=None):
        """Force keep_alive=0 to unload the model from VRAM."""
        try:
            requests.post(self.api_url, json={
                "model": model,
                "keep_alive": 0
            }, timeout=5)
            if logger:
                logger.info(f"🧹 已成功向 Ollama 發送卸載指令，釋放 {model} 佔用之記憶體。")
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ 無法釋放 Ollama 記憶體: {e}")
