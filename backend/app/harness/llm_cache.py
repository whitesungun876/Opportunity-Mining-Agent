"""SQLite-backed cache for structured LLM responses."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


def stable_hash(value: Any) -> str:
    """Hash JSON-serializable content with stable key ordering."""
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class LLMCache:
    """Small thread-safe SQLite cache for local live runs."""

    def __init__(self, path: str | Path = "./data/llm_cache.sqlite") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_cache (
                cache_key TEXT PRIMARY KEY,
                response_json TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    def get(self, cache_key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT response_json FROM llm_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def set(self, cache_key: str, response: dict[str, Any]) -> None:
        response_json = json.dumps(response, ensure_ascii=False, sort_keys=True, default=str)
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO llm_cache (cache_key, response_json, created_at)
                VALUES (?, ?, ?)
                """,
                (cache_key, response_json, time.time()),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
