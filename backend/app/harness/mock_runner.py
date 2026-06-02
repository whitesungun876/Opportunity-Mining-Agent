"""Mock runner helpers."""

from __future__ import annotations


def is_mock_mode() -> bool:
    """MVP defaults to mock mode unless explicitly replaced by real clients."""
    return True
