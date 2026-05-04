"""
core/llm_client.py — Ollama / OpenAI-Compatible LLM Client (V2.1)
==================================================================
V2.1 Changes:
- Circuit Breaker: after N consecutive failures, switches to models.fallback from config
- Trace ID: accepts optional trace_id for distributed log correlation
- Exponential Backoff: refined to use 2^attempt × backoff_seconds formula
"""

import contextvars
import hashlib
import os
import sqlite3
import time
from typing import Any, Dict, NamedTuple, Optional, Tuple, Union

import aiohttp
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

TimeoutType = Union[float, Tuple[float, float]]

# ---------------------------------------------------------------------------
# Distributed Trace ID — Thread-local context variable (#12)
# ---------------------------------------------------------------------------
# Set this at the top of each orchestrator run_all.py invocation:
#   from core.ai.llm_client import TRACE_ID_VAR
#   TRACE_ID_VAR.set(str(uuid.uuid4()))
TRACE_ID_VAR: contextvars.ContextVar[str] = contextvars.ContextVar("openclaw_trace_id", default="")


# ---------------------------------------------------------------------------
# P2-5: GenerateResult — enriched return type for observability
# ---------------------------------------------------------------------------


class GenerateResult(str):
    """Immutable str subclass carrying LLM generation metadata.

    Behaves exactly like a plain ``str`` so all existing callers
    (``result.split()``, ``len(result)``, f-strings, etc.) continue to work
    without modification.  Extra attributes are available for evaluation
    pipelines and dashboards.

    Attributes:
        text:        The raw LLM response text (same as the str value).
        latency_ms:  Wall-clock time from request start to first byte (ms).
        token_count: Approximate token count from the API response, if available.
        model:       The effective model that produced the response.
    """

    # Declare typed attributes so Mypy can resolve them
    latency_ms: float
    token_count: int
    model: str

    def __new__(cls, text: str, latency_ms: float = 0.0, token_count: int = 0, model: str = ""):
        instance = super().__new__(cls, text)
        instance.latency_ms = latency_ms
        instance.token_count = token_count
        instance.model = model
        return instance

    def __repr__(self) -> str:
        return (
            f"GenerateResult({str.__repr__(self)}, "
            f"latency_ms={self.latency_ms:.0f}, "
            f"token_count={self.token_count}, "
            f"model={self.model!r})"
        )


# ---------------------------------------------------------------------------
# Semantic Cache (SQLite)
# ---------------------------------------------------------------------------


class SqliteSemanticCache:
    """Thread-safe SQLite cache for deterministic LLM generation."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_cache (
                    hash_key TEXT PRIMARY KEY,
                    model TEXT,
                    prompt TEXT,
                    response TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def _hash(self, model: str, prompt: str) -> str:
        raw = f"{model}::{prompt}".encode()
        return hashlib.sha256(raw).hexdigest()

    def get(self, model: str, prompt: str) -> Optional[str]:
        hash_key = self._hash(model, prompt)
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.execute(
                    "SELECT response FROM semantic_cache WHERE hash_key = ?", (hash_key,)
                )
                row = cursor.fetchone()
                if row:
                    return row[0]
        except Exception:
            pass
        return None

    def set(self, model: str, prompt: str, response: str) -> None:
        hash_key = self._hash(model, prompt)
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO semantic_cache (hash_key, model, prompt, response)
                    VALUES (?, ?, ?, ?)
                    """,
                    (hash_key, model, prompt, response),
                )
                conn.commit()
        except Exception:
            pass


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

        # Semantic cache initialization
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        cache_db_path = os.path.join(workspace_root, "data", "llm_cache.sqlite3")
        self._cache = SqliteSemanticCache(cache_db_path)

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

        # Context-Aware Routing Override
        effective_model = os.environ.get("OPENCLAW_ROUTER_MODEL", model)

        # Circuit breaker: if open and fallback available, switch model silently
        if self._circuit_open and self.fallback_model and self.fallback_model != effective_model:
            if logger:
                logger.warning(
                    f"{trace_pfx}⚡ Circuit Breaker 已觸發：自動切換 {effective_model} → {self.fallback_model}"
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

        # P1.1: Security Manager - LLMGuard Prompt Injection Filter
        if os.environ.get("OPENCLAW_ENABLE_LLMGUARD", "1") == "1":
            try:
                from llm_guard.input_scanners import PromptInjection
                from llm_guard.input_scanners.prompt_injection import MatchType

                # We instantiate it lazily to avoid heavy loading on import.
                # In a real production environment, this should be cached in SecurityManager.
                scanner = PromptInjection(threshold=0.8, match_type=MatchType.FULL)
                _, is_valid, risk_score = scanner.scan(prompt)

                if risk_score > 0.8:
                    if logger:
                        logger.error(
                            f"{trace_pfx}🚨 LLMGuard 攔截到潛在的 Prompt Injection 攻擊！(風險值: {risk_score:.2f})"
                        )
                    raise ValueError(f"Prompt injection detected (Risk: {risk_score:.2f})")
            except ImportError:
                if logger:
                    logger.debug(f"{trace_pfx}⚠️ llm-guard 未安裝，略過 Prompt Injection 檢查。")

        # Semantic Caching Check (only for deterministic calls)
        temperature = (options or {}).get("temperature", 0)
        if temperature == 0:
            cached_response = self._cache.get(effective_model, prompt)
            if cached_response:
                if logger:
                    logger.info(f"{trace_pfx}⚡ 命中語意快取 (Semantic Cache)，跳過推理。")
                return GenerateResult(
                    cached_response,
                    latency_ms=1.0,
                    token_count=0,
                    model=effective_model,
                )

        t_start = time.monotonic()  # P2-5: latency tracking
        for attempt in range(self.retries):
            try:
                res = requests.post(self.api_url, json=payload, timeout=self.timeout)
                res.raise_for_status()

                _resp_json = res.json()
                if is_openai:
                    response_text = (
                        _resp_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                    )
                    _token_count = _resp_json.get("usage", {}).get("completion_tokens", 0)
                else:
                    response_text = _resp_json.get("response", "")
                    # P2-5: Ollama returns eval_count (output tokens) in generate response
                    _token_count = _resp_json.get("eval_count", 0)

                if not response_text or not response_text.strip():
                    raise ValueError(
                        "API 回傳空內容（可能原因：num_predict 耗盡、網路超時、模型載入失敗）"
                    )

                # Successful call — reset circuit breaker
                self._consecutive_failures = 0
                self._circuit_open = False

                # P2-5: Return GenerateResult (str subclass) with observability metadata
                _latency_ms = (time.monotonic() - t_start) * 1000

                # Cache deterministic responses
                if temperature == 0:
                    self._cache.set(effective_model, prompt, response_text)

                return GenerateResult(
                    response_text,
                    latency_ms=_latency_ms,
                    token_count=_token_count,
                    model=effective_model,
                )

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

    # ------------------------------------------------------------------ #
    #  Async / Concurrent Generation (#16)                                #
    # ------------------------------------------------------------------ #

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((aiohttp.ClientError, TimeoutError, ValueError)),
    )
    async def async_generate(
        self,
        model: str,
        prompt: str,
        options: Optional[Dict[str, Any]] = None,
        images: Optional[list] = None,
        logger=None,
    ) -> str:
        """Fully async generation using aiohttp and tenacity (P4.2)."""
        trace_id = TRACE_ID_VAR.get()
        trace_pfx = f"[trace:{trace_id[:8]}] " if trace_id else ""

        # Context-Aware Routing Override
        effective_model = os.environ.get("OPENCLAW_ROUTER_MODEL", model)

        if self._circuit_open and self.fallback_model and self.fallback_model != effective_model:
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

        # P1.1: Security Manager - LLMGuard Prompt Injection Filter
        if os.environ.get("OPENCLAW_ENABLE_LLMGUARD", "1") == "1":
            try:
                from llm_guard.input_scanners import PromptInjection
                from llm_guard.input_scanners.prompt_injection import MatchType

                scanner = PromptInjection(threshold=0.8, match_type=MatchType.FULL)
                _, is_valid, risk_score = scanner.scan(prompt)

                if risk_score > 0.8:
                    if logger:
                        logger.error(
                            f"{trace_pfx}🚨 LLMGuard 攔截到潛在的 Prompt Injection 攻擊！(風險值: {risk_score:.2f})"
                        )
                    raise ValueError(f"Prompt injection detected (Risk: {risk_score:.2f})")
            except ImportError:
                if logger:
                    logger.debug(f"{trace_pfx}⚠️ llm-guard 未安裝，略過 Prompt Injection 檢查。")

        # Semantic Caching Check (only for deterministic calls)
        temperature = (options or {}).get("temperature", 0)
        if temperature == 0:
            cached_response = self._cache.get(effective_model, prompt)
            if cached_response:
                if logger:
                    logger.info(f"{trace_pfx}⚡ 命中語意快取 (Semantic Cache)，跳過推理 (Async)。")
                return GenerateResult(
                    cached_response,
                    latency_ms=1.0,
                    token_count=0,
                    model=effective_model,
                )

        t_start = time.monotonic()
        timeout_val = self.timeout[0] if isinstance(self.timeout, tuple) else self.timeout

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.api_url, json=payload, timeout=timeout_val) as res:
                    res.raise_for_status()
                    _resp_json = await res.json()

                    if is_openai:
                        response_text = (
                            _resp_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                        )
                        _token_count = _resp_json.get("usage", {}).get("completion_tokens", 0)
                    else:
                        response_text = _resp_json.get("response", "")
                        _token_count = _resp_json.get("eval_count", 0)

                    if not response_text or not response_text.strip():
                        raise ValueError("API 回傳空內容")

                    self._consecutive_failures = 0
                    self._circuit_open = False
                    _latency_ms = (time.monotonic() - t_start) * 1000

                    # Cache deterministic responses
                    if temperature == 0:
                        self._cache.set(effective_model, prompt, response_text)

                    return GenerateResult(
                        response_text,
                        latency_ms=_latency_ms,
                        token_count=_token_count,
                        model=effective_model,
                    )
            except Exception as e:
                self._consecutive_failures += 1
                if self._consecutive_failures >= self.CIRCUIT_BREAKER_THRESHOLD:
                    self._circuit_open = True
                    if logger:
                        logger.error(
                            f"{trace_pfx}⚡ Circuit Breaker 已開路！自動切換至 {self.fallback_model}"
                        )
                if logger:
                    logger.warning(f"{trace_pfx}LLM API 請求失敗 ({e})，觸發 Tenacity 退避重試...")
                raise e

    async def async_batch_generate(
        self,
        model: str,
        prompts: list,
        options: Optional[Dict[str, Any]] = None,
        max_concurrency: int = 3,
        logger=None,
    ) -> list:
        """Concurrently generate responses for multiple prompts with a semaphore cap.

        Uses asyncio.Semaphore to limit simultaneous Ollama API calls, preventing
        OOM while still achieving 2–4× throughput vs sequential processing.

        Args:
            model:           Model name for all prompts.
            prompts:         List of prompt strings (one per chunk).
            options:         Shared generation options.
            max_concurrency: Maximum simultaneous in-flight requests (default 3).
                             Tune down if RAM is tight; tune up on powerful machines.
            logger:          Optional logger instance.

        Returns:
            List of response strings in the same order as prompts.
            Failed prompts return empty string "" (caller should handle fallback).

        Example (in a Phase script):
            import asyncio
            results = asyncio.run(self.llm.async_batch_generate(
                model=model_name,
                prompts=[build_prompt(c) for c in chunks],
                max_concurrency=3,
            ))
        """
        import asyncio

        semaphore = asyncio.Semaphore(max_concurrency)
        trace_id = TRACE_ID_VAR.get()
        trace_pfx = f"[trace:{trace_id[:8]}] " if trace_id else ""

        async def _safe_generate(idx: int, prompt: str) -> tuple:
            async with semaphore:
                try:
                    result = await self.async_generate(
                        model=model,
                        prompt=prompt,
                        options=options,
                        logger=logger,
                    )
                    return idx, result
                except Exception as exc:
                    if logger:
                        logger.warning(f"{trace_pfx}[async_batch] 片段 {idx} 失敗: {exc}")
                    return idx, ""

        tasks = [_safe_generate(i, p) for i, p in enumerate(prompts)]
        pairs = await asyncio.gather(*tasks)
        # Restore original order
        ordered = [""] * len(prompts)
        for idx, text in pairs:
            ordered[idx] = text
        return ordered
