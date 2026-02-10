"""LangGraph checkpointer: resume from checkpoint and state replay."""

from __future__ import annotations

from typing import Any

# LangGraph MemorySaver or SqliteSaver can be wrapped here;
# pass checkpointer when compiling the graph to enable checkpointing.


def get_checkpointer(backend: str = "memory", **kwargs: Any) -> Any:
    """Return a LangGraph-compatible checkpointer."""
    if backend == "memory":
        try:
            from langgraph.checkpoint.memory import MemorySaver
            return MemorySaver()
        except ImportError:
            return None
    if backend == "sqlite":
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            path = kwargs.get("path", "./data/checkpoints.db")
            return SqliteSaver.from_conn_string(path)
        except ImportError:
            return None
    return None
