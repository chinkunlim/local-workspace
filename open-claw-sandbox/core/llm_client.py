"""
core/llm_client.py — Ollama / OpenAI-Compatible LLM Client (V2.1)
==================================================================
V2.1 Changes:
- Circuit Breaker: after N consecutive failures, switches to models.fallback from config
- Trace ID: accepts optional trace_id for distributed log correlation
- Exponential Backoff: refined to use 2^attempt × backoff_seconds formula
"""

import contextvars
import os
import time
from typing import Any, Dict, Optional, Tuple, Union

import requests

TimeoutType = Union[float, Tuple[float, float]]

# ---------------------------------------------------------------------------
# Distributed Trace ID — Thread-local context variable (#12)
# ---------------------------------------------------------------------------
# Set this at the top of each orchestrator run_all.py invocation:
#   from core.llm_client import TRACE_ID_VAR
#   TRACE_ID_VAR.set(str(uuid.uuid4()))
TRACE_ID_VAR: contextvars.ContextVar[str] = contextvars.ContextVar("openclaw_trace_id", default="")


class OllamaClient:
    # Number of consecutive failures before triggering circuit breaker
    CIRCUIT_BREAKER_THRESHOLD = 3

    def __init__(
        self,
        api_url: Optional[str] = None,
        timeout: TimeoutType = 600,
        retries: int = 3,
        backoff_seconds: float = 5.0,
        fallback_model: Optional[str] = None,
    ):
        self.api_url = api_url or os.environ.get("OLLAMA_API_URL", "")
        if not self.api_url:
            raise ValueError("Ollama API URL is required. Provide it via config or OLLAMA_API_URL.")
        assert self.api_url is not None
        self.timeout = timeout
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.fallback_model = fallback_model  # Circuit breaker fallback (#11)

        # Circuit breaker state
        self._consecutive_failures: int = 0
        self._circuit_open: bool = False

    def generate(
        self,
        model: str,
        prompt: str,
        options: Optional[Dict[str, Any]] = None,
        images: Optional[list] = None,
        logger=None,
    ) -> str:
        """Call Ollama generation endpoint or LM Studio / OpenAI endpoint dynamically.

        Includes:
        - Exponential backoff retry (V1 behaviour preserved)
        - Circuit Breaker: on CIRCUIT_BREAKER_THRESHOLD consecutive failures,
          auto-switches to self.fallback_model if configured (#11)
        - Emits trace_id in log messages when available (#12)
        """
        trace_id = TRACE_ID_VAR.get()
        trace_pfx = f"[trace:{trace_id[:8]}] " if trace_id else ""

        # Circuit breaker: if open and fallback available, switch model silently
        effective_model = model
        if self._circuit_open and self.fallback_model and self.fallback_model != model:
            if logger:
                logger.warning(
                    f"{trace_pfx}⚡ Circuit Breaker 已觸發：自動切換 {model} → {self.fallback_model}"
                )
            effective_model = self.fallback_model

        is_openai = "/v1" in self.api_url or "chat/completions" in self.api_url

        if is_openai:
            payload = {
                "model": effective_model,
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
            payload = {"model": effective_model, "prompt": prompt, "stream": False}
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

                # Successful call — reset circuit breaker
                self._consecutive_failures = 0
                self._circuit_open = False
                return response_text

            except requests.exceptions.RequestException as e:
                error_body = ""
                if hasattr(e, "response") and e.response is not None:
                    error_body = f" - Body: {e.response.text}"
                full_error = f"{e}{error_body}"

                if attempt < self.retries - 1:
                    wait = self.backoff_seconds * (2**attempt)
                    if logger:
                        logger.warning(
                            f"{trace_pfx}LLM API 請求失敗 ({full_error})，"
                            f"{wait:.1f}s 後進行第 {attempt + 2} 次重試..."
                        )
                    time.sleep(wait)
                else:
                    # Update circuit breaker state
                    self._consecutive_failures += 1
                    if self._consecutive_failures >= self.CIRCUIT_BREAKER_THRESHOLD:
                        self._circuit_open = True
                        if logger:
                            logger.error(
                                f"{trace_pfx}⚡ Circuit Breaker 已開路！"
                                f"連續失敗 {self._consecutive_failures} 次。"
                                f"{'fallback: ' + (self.fallback_model or 'N/A')}"
                            )

                    if logger:
                        logger.error(f"{trace_pfx}LLM API 請求徹底失敗: {full_error}")
                    raise RuntimeError(f"API 請求失敗: {full_error}")

        raise RuntimeError("LLM API request failed (retries exhausted or zero retries)")

    def unload_model(self, model: str, logger=None):
        """Force keep_alive=0 to unload the model from VRAM."""
        trace_id = TRACE_ID_VAR.get()
        trace_pfx = f"[trace:{trace_id[:8]}] " if trace_id else ""
        try:
            requests.post(self.api_url, json={"model": model, "keep_alive": 0}, timeout=5)
            if logger:
                logger.info(
                    f"{trace_pfx}🧹 已成功向 Ollama 發送卸載指令，釋放 {model} 佔用之記憶體。"
                )
        except Exception as e:
            if logger:
                logger.warning(f"{trace_pfx}⚠️ 無法釋放 Ollama 記憶體: {e}")
