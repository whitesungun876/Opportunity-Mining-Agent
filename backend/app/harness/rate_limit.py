"""Simple rate-limit placeholder."""

from __future__ import annotations

import time


class RateLimiter:
    """Sleep-based limiter for future real GitHub/LLM clients."""

    def __init__(self, min_interval_seconds: float = 0.0) -> None:
        self.min_interval_seconds = min_interval_seconds
        self._last_call = 0.0

    def wait(self) -> None:
        now = time.perf_counter()
        delay = self.min_interval_seconds - (now - self._last_call)
        if delay > 0:
            time.sleep(delay)
        self._last_call = time.perf_counter()
