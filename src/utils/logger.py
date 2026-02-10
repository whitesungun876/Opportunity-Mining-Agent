"""Logging and optional structured (JSON) output for observability."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

# .env can set LOG_LEVEL; LangSmith reads LANGCHAIN_* for tracing
def configure_logging(level: str = "INFO", **kwargs: Any) -> None:
    """Configure root logger; compatible with LangSmith tracing."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        **kwargs,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    _configure_structured_logging()


def _configure_structured_logging() -> None:
    """
    When LOG_STRUCTURED=1, write one JSON line per node event to a file (or stderr).
    Logger 'src.utils.observability.structured' gets a handler with format '%(message)s'.
    """
    if os.getenv("LOG_STRUCTURED", "").strip() != "1":
        return
    struct_logger = logging.getLogger("src.utils.observability.structured")
    struct_logger.setLevel(logging.INFO)
    struct_logger.propagate = False
    out = os.getenv("LOG_STRUCTURED_FILE", "").strip()
    if out:
        path = Path(out).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, encoding="utf-8")
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    struct_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
