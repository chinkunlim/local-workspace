# -*- coding: utf-8 -*-
import json
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
        self.timeout = timeout if isinstance(timeout, (int, float)) else timeout[1]
        self.retries = retries
        self.backoff_seconds = backoff_seconds

    def generate(self, model: str, prompt: str, options: Optional[Dict[str, Any]] = None, images: Optional[list] = None, logger=None) -> str:
        """Call Ollama generation endpoint with streaming to avoid terminal freeze."""
        is_openai = "/v1" in self.api_url or "chat/completions" in self.api_url

        if is_openai:
            # LM Studio / OpenAI Standard Format (streaming)
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
            }
            if options:
                if "temperature" in options: payload["temperature"] = options["temperature"]
                if "num_predict" in options: payload["max_tokens"] = options["num_predict"]
                if "max_tokens" in options: payload["max_tokens"] = options["max_tokens"]
        else:
            # Ollama Direct Format (streaming)
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True,
            }
            if options: payload["options"] = options
            if images: payload["images"] = images

        for attempt in range(self.retries):
            try:
                response_text = self._stream_request(payload, is_openai)
                if not response_text or not response_text.strip():
                    raise ValueError("API 回傳空內容（可能原因：num_predict 耗盡、網路超時、模型載入失敗）")
                return response_text

            except (requests.exceptions.RequestException, TimeoutError, ValueError) as e:
                if attempt < self.retries - 1:
                    if logger:
                        logger.warning(f"LLM API 請求失敗 ({e})，正在進行第 {attempt + 2} 次重試...")
                    time.sleep(self.backoff_seconds * (2 ** attempt))
                else:
                    if logger:
                        logger.error(f"LLM API 請求徹底失敗: {e}")
                    raise RuntimeError(f"API 請求失敗: {e}")

    def _stream_request(self, payload: dict, is_openai: bool) -> str:
        """
        以 streaming 模式發送請求，逐 token 接收並印出進度點（每 50 token 印一點）。
        整體受 self.timeout 秒保護；超時則拋出 TimeoutError。
        """
        deadline    = time.monotonic() + self.timeout
        chunks      = []
        token_count = 0

        # connect_timeout=10s, read_timeout=None（由我們自己透過 deadline 控制）
        with requests.post(
            self.api_url,
            json=payload,
            stream=True,
            timeout=(10, None),
        ) as resp:
            resp.raise_for_status()

            for raw_line in resp.iter_lines():
                if time.monotonic() > deadline:
                    raise TimeoutError(
                        f"LLM 生成超時（{self.timeout}s），已中止。"
                    )
                if not raw_line:
                    continue

                try:
                    data = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                if is_openai:
                    # SSE format
                    delta   = data.get("choices", [{}])[0].get("delta", {})
                    token   = delta.get("content", "")
                    is_done = data.get("choices", [{}])[0].get("finish_reason") is not None
                else:
                    token   = data.get("response", "")
                    is_done = data.get("done", False)

                if token:
                    chunks.append(token)
                    token_count += 1
                    # 每 50 token 印一點，讓使用者知道還在跑
                    if token_count % 50 == 0:
                        print(".", end="", flush=True)

                if is_done:
                    break

        if token_count > 0:
            print()  # 換行（結束進度點列）

        return "".join(chunks)

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
