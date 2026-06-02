"""Small in-memory cache for preflight warm-start state."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any


class PreflightCache:
    """Process-local TTL cache.

    The preflight endpoint already performs a cheap GitHub probe and evidence
    ranking. Keeping that state briefly lets the full run skip duplicate GitHub
    collection when the user immediately confirms the same query.
    """

    def __init__(self, ttl_seconds: int = 900) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._items: dict[str, tuple[datetime, dict[str, Any]]] = {}
        self._lock = Lock()

    def set(self, preflight_id: str, state: dict[str, Any]) -> None:
        expires_at = datetime.now(UTC) + self._ttl
        with self._lock:
            self._items[preflight_id] = (expires_at, deepcopy(state))
            self._prune_locked()

    def get(self, preflight_id: str) -> dict[str, Any] | None:
        with self._lock:
            self._prune_locked()
            item = self._items.get(preflight_id)
            if item is None:
                return None
            expires_at, state = item
            if expires_at < datetime.now(UTC):
                self._items.pop(preflight_id, None)
                return None
            return deepcopy(state)

    def _prune_locked(self) -> None:
        now = datetime.now(UTC)
        expired = [key for key, (expires_at, _) in self._items.items() if expires_at < now]
        for key in expired:
            self._items.pop(key, None)


preflight_cache = PreflightCache()


def get_preflight_initial_state(preflight_id: str | None) -> dict[str, Any] | None:
    if not preflight_id:
        return None
    return preflight_cache.get(preflight_id)
