"""Deterministic truncation utilities."""

from __future__ import annotations


def truncate_text(text: str, max_chars: int) -> str:
    """Truncate text without adding model-facing ambiguity."""
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 15)].rstrip() + " [truncated]"


def truncate_items(items: list[dict], max_items: int) -> list[dict]:
    """Keep first N structured items for mock MVP context control."""
    return list(items[:max_items])
