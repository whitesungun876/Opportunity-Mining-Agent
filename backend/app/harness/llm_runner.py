"""Bounded-concurrency runner for LLM-heavy node work."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Iterable, TypeVar


T = TypeVar("T")
R = TypeVar("R")


class LLMRunner:
    """Run independent LLM tasks concurrently while preserving result order."""

    def __init__(self, *, max_concurrency: int = 4) -> None:
        self.max_concurrency = max(1, int(max_concurrency or 1))

    def run_many(self, items: Iterable[T], fn: Callable[[T], R]) -> list[R]:
        work_items = list(items)
        if not work_items:
            return []
        if self.max_concurrency <= 1 or len(work_items) == 1:
            return [fn(item) for item in work_items]

        results: list[Any] = [None] * len(work_items)
        workers = min(self.max_concurrency, len(work_items))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(fn, item): idx for idx, item in enumerate(work_items)}
            for future in as_completed(futures):
                results[futures[future]] = future.result()
        return results
