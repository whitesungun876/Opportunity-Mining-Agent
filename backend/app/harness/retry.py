"""Retry helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


def retry(fn: Callable[[], T], retry_limit: int = 2) -> T:
    """Tiny retry helper for non-tool code paths."""
    last_error: Exception | None = None
    for _ in range(retry_limit + 1):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
    raise RuntimeError(str(last_error))
