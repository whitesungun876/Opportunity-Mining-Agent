"""OpenAI-compatible LLM client abstraction."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from typing import Any

import httpx

from app.harness.llm_cache import LLMCache, stable_hash


class LLMClientError(RuntimeError):
    """Raised when an OpenAI-compatible LLM request fails."""


def parse_json_object(value: str | dict[str, Any]) -> dict[str, Any]:
    """Parse a JSON object from model content, accepting fenced JSON as fallback."""
    if isinstance(value, dict):
        return value
    text = value.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("LLM response must be a JSON object")
    return parsed


class LLMClient:
    """Synchronous OpenAI-compatible chat completions client."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        mock_mode: bool = True,
        timeout_seconds: float = 30.0,
        retry_limit: int = 2,
        backoff_seconds: float = 1.0,
        cache: LLMCache | None = None,
        cache_enabled: bool | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.model = model or os.getenv("LLM_MODEL") or os.getenv("DEFAULT_MODEL") or "gpt-4o-mini"
        self.mock_mode = mock_mode
        self.timeout_seconds = timeout_seconds
        self.retry_limit = retry_limit
        self.backoff_seconds = backoff_seconds
        self.cache_enabled = (
            (os.getenv("LLM_CACHE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"})
            if cache_enabled is None
            else cache_enabled
        )
        self.cache = cache
        if self.cache is None and self.cache_enabled and not self.mock_mode:
            self.cache = LLMCache(os.getenv("LLM_CACHE_PATH", "./data/llm_cache.sqlite"))
        self._client: httpx.Client | None = None
        self._client_lock = threading.Lock()

    @property
    def chat_completions_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def close(self) -> None:
        with self._client_lock:
            if self._client is not None:
                self._client.close()
                self._client = None

    def __enter__(self) -> "LLMClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _http_client(self) -> httpx.Client:
        with self._client_lock:
            if self._client is None:
                self._client = httpx.Client(timeout=self.timeout_seconds)
            return self._client

    def _cache_key(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        system_prompt: str | None,
    ) -> str:
        return stable_hash(
            {
                "base_url": self.base_url,
                "model": self.model,
                "prompt": prompt,
                "schema": schema,
                "system_prompt": system_prompt,
            }
        )

    def structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Return a structured JSON object from an OpenAI-compatible chat model."""
        if self.mock_mode:
            return {"mock": True, "prompt_preview": prompt[:120], "schema": schema}
        if not self.api_key:
            raise LLMClientError("LLM_API_KEY is required for real LLM mode")

        cache_key = self._cache_key(prompt=prompt, schema=schema, system_prompt=system_prompt)
        if self.cache_enabled and self.cache is not None:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append(
            {
                "role": "user",
                "content": prompt
                + "\n\nReturn strict JSON only. Do not include markdown or explanatory text.",
            }
        )
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(self.retry_limit + 1):
            try:
                response = self._http_client().post(self.chat_completions_url, json=payload, headers=headers)
                if response.status_code in {429, 500, 502, 503, 504} and attempt < self.retry_limit:
                    time.sleep(self.backoff_seconds * (attempt + 1))
                    continue
                response.raise_for_status()
                body = response.json()
                content = (((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
                if not content:
                    raise LLMClientError("empty LLM response content")
                parsed = parse_json_object(content)
                if self.cache_enabled and self.cache is not None:
                    self.cache.set(cache_key, parsed)
                return parsed
            except (httpx.HTTPError, ValueError, KeyError, LLMClientError) as exc:
                last_error = exc
                if attempt < self.retry_limit:
                    time.sleep(self.backoff_seconds * (attempt + 1))
                    continue
                break
        raise LLMClientError(str(last_error))
