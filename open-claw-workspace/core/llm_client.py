import os
import time
from typing import Any, Dict, Optional, Tuple, Union

import requests


TimeoutType = Union[float, Tuple[float, float]]

class OllamaClient:
    def __init__(self, api_url: Optional[str] = None, timeout: TimeoutType = 600, retries: int = 3, backoff_seconds: float = 5.0):
        self.api_url = api_url or os.environ.get("OLLAMA_API_URL")
        if not self.api_url:
            raise ValueError("Ollama API URL is required. Provide it via config or OLLAMA_API_URL.")
        self.timeout = timeout
        self.retries = retries
        self.backoff_seconds = backoff_seconds

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
                    time.sleep(self.backoff_seconds * (2 ** attempt))
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
