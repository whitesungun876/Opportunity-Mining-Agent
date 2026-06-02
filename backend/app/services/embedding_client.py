"""OpenAI-compatible embedding client with deterministic fallback."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import threading
from typing import Any

import httpx


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_BASE_URL = "https://api.openai.com/v1"
MOCK_DIMENSIONS = 64


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9_+-]*", text.lower())


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def deterministic_embedding(text: str, dimensions: int = MOCK_DIMENSIONS) -> list[float]:
    """Create a stable bag-of-token hash embedding for fallback similarity."""
    vector = [0.0] * dimensions
    for token in _tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % dimensions
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vector[idx] += sign
    return _normalize(vector)


class EmbeddingCache:
    """Small SQLite cache for embeddings."""

    def __init__(self, path: str | Path = "./data/embedding_cache.sqlite") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embedding_cache (
                cache_key TEXT PRIMARY KEY,
                vector_json TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def get(self, cache_key: str) -> list[float] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT vector_json FROM embedding_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
        if row is None:
            return None
        return [float(item) for item in json.loads(row[0])]

    def set(self, cache_key: str, vector: list[float]) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO embedding_cache (cache_key, vector_json) VALUES (?, ?)",
                (cache_key, json.dumps(vector)),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class EmbeddingClient:
    """OpenAI-compatible embedding client with deterministic fallback."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 30.0,
        cache_enabled: bool | None = None,
        cache_path: str | Path | None = None,
        mock_mode: bool | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("EMBEDDING_API_KEY")
        self.base_url = (base_url or os.getenv("EMBEDDING_BASE_URL") or DEFAULT_EMBEDDING_BASE_URL).rstrip("/")
        self.model = model or os.getenv("EMBEDDING_MODEL") or DEFAULT_EMBEDDING_MODEL
        self.timeout_seconds = timeout_seconds
        self.mock_mode = (mock_mode if mock_mode is not None else not bool(self.api_key))
        self.cache_enabled = _env_bool("EMBEDDING_CACHE_ENABLED", True) if cache_enabled is None else cache_enabled
        self.cache_path = Path(cache_path or os.getenv("EMBEDDING_CACHE_PATH", "./data/embedding_cache.sqlite"))
        self.cache = EmbeddingCache(self.cache_path) if self.cache_enabled else None
        self._client: httpx.Client | None = None

    def __enter__(self) -> "EmbeddingClient":
        if not self.mock_mode:
            self._client = httpx.Client(timeout=self.timeout_seconds)
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
        if self.cache is not None:
            self.cache.close()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.embed_batch(texts)

    def embed_batch(self, texts: list[str], *, batch_size: int = 64) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float] | None] = [None] * len(texts)
        missing: list[tuple[int, str, str]] = []
        for idx, text in enumerate(texts):
            key = self._cache_key(text)
            cached = self.cache.get(key) if self.cache else None
            if cached is not None:
                vectors[idx] = cached
            else:
                missing.append((idx, text, key))

        for start in range(0, len(missing), batch_size):
            batch = missing[start:start + batch_size]
            batch_vectors = self._embed_uncached([text for _, text, _ in batch])
            for (idx, _text, key), vector in zip(batch, batch_vectors):
                vectors[idx] = vector
                if self.cache is not None:
                    self.cache.set(key, vector)
        return [vector or deterministic_embedding("") for vector in vectors]

    def _cache_key(self, text: str) -> str:
        return _stable_hash({"provider": "embedding", "base_url": self.base_url, "model": self.model, "text": text})

    def _embed_uncached(self, texts: list[str]) -> list[list[float]]:
        if self.mock_mode or not self.api_key:
            return [deterministic_embedding(text) for text in texts]
        client = self._client or httpx.Client(timeout=self.timeout_seconds)
        close_client = self._client is None
        try:
            response = client.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "input": texts},
            )
            response.raise_for_status()
            data = response.json().get("data") or []
            by_index = sorted(data, key=lambda item: item.get("index", 0))
            vectors = [[float(value) for value in item.get("embedding", [])] for item in by_index]
            if len(vectors) != len(texts):
                raise ValueError("embedding response count mismatch")
            return vectors
        except Exception:
            return [deterministic_embedding(text) for text in texts]
        finally:
            if close_client:
                client.close()
