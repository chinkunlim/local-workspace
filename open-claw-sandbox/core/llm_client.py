import os
import time
from typing import Any, Dict, Optional, Tuple, Union

import requests

TimeoutType = Union[float, Tuple[float, float]]


class OllamaClient:
    def __init__(
        self,
        api_url: Optional[str] = None,
        timeout: TimeoutType = 600,
        retries: int = 3,
        backoff_seconds: float = 5.0,
    ):
        self.api_url = api_url or os.environ.get("OLLAMA_API_URL", "")
        if not self.api_url:
            raise ValueError("Ollama API URL is required. Provide it via config or OLLAMA_API_URL.")
        assert self.api_url is not None
        self.timeout = timeout
        self.retries = retries
        self.backoff_seconds = backoff_seconds

    def generate(
        self,
        model: str,
        prompt: str,
        options: Optional[Dict[str, Any]] = None,
        images: Optional[list] = None,
        logger=None,
    ) -> str:
        """Call Ollama generation endpoint or LM Studio / OpenAI endpoint dynamically."""
        is_openai = "/v1" in self.api_url or "chat/completions" in self.api_url

        if is_openai:
            # LM Studio / OpenAI Standard Format
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
            if options:
                if "temperature" in options:
                    payload["temperature"] = options["temperature"]
                if "num_predict" in options:
                    payload["max_tokens"] = options["num_predict"]
                if "max_tokens" in options:
                    payload["max_tokens"] = options["max_tokens"]
        else:
            # Original Ollama Direct Format
            payload = {"model": model, "prompt": prompt, "stream": False}
            if options:
                payload["options"] = options
            if images:
                payload["images"] = images

        for attempt in range(self.retries):
            try:
                res = requests.post(self.api_url, json=payload, timeout=self.timeout)
                res.raise_for_status()

                if is_openai:
                    response_text = (
                        res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                    )
                else:
                    response_text = res.json().get("response", "")

                if not response_text or not response_text.strip():
                    raise ValueError(
                        "API 回傳空內容（可能原因：num_predict 耗盡、網路超時、模型載入失敗）"
                    )
                return response_text
            except requests.exceptions.RequestException as e:
                error_body = ""
                if hasattr(e, "response") and e.response is not None:
                    error_body = f" - Body: {e.response.text}"
                full_error = f"{e}{error_body}"

                if attempt < self.retries - 1:
                    if logger:
                        logger.warning(
                            f"LLM API 請求失敗 ({full_error})，正在進行第 {attempt + 2} 次重試..."
                        )
                    time.sleep(self.backoff_seconds * (2**attempt))
                else:
                    if logger:
                        logger.error(f"LLM API 請求徹底失敗: {full_error}")
                    raise RuntimeError(f"API 請求失敗: {full_error}")

        raise RuntimeError("LLM API request failed (retries exhausted or zero retries)")

    def unload_model(self, model: str, logger=None):
        """Force keep_alive=0 to unload the model from VRAM."""
        try:
            requests.post(self.api_url, json={"model": model, "keep_alive": 0}, timeout=5)
            if logger:
                logger.info(f"🧹 已成功向 Ollama 發送卸載指令，釋放 {model} 佔用之記憶體。")
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ 無法釋放 Ollama 記憶體: {e}")
