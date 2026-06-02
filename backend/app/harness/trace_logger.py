"""JSON trace logger for graph and tool execution."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any


def summarize(value: Any) -> dict[str, Any]:
    """Return a compact summary suitable for trace logs."""
    if isinstance(value, list):
        return {"type": "list", "count": len(value)}
    if isinstance(value, dict):
        summary: dict[str, Any] = {"type": "dict", "keys": sorted(list(value.keys()))[:20]}
        for key, item in value.items():
            if isinstance(item, list):
                summary[f"{key}_count"] = len(item)
        return summary
    return {"type": type(value).__name__, "repr": str(value)[:160]}


class JsonTraceLogger:
    """Append-only JSONL trace logger."""

    def __init__(self, path: str | Path = "./data/traces.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def log(
        self,
        *,
        run_id: str,
        node_name: str,
        input_data: Any,
        output_data: Any = None,
        latency_ms: float = 0.0,
        errors: list[str] | None = None,
        prompt_version: str = "mock:v1",
        model: str = "mock-llm",
        token_usage: dict[str, int] | None = None,
        is_mock: bool = True,
    ) -> None:
        payload = {
            "ts": time.time(),
            "run_id": run_id,
            "node_name": node_name,
            "input_summary": summarize(input_data),
            "output_summary": summarize(output_data),
            "latency_ms": round(latency_ms, 2),
            "errors": errors or [],
            "prompt_version": prompt_version,
            "model": model,
            "token_usage": token_usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "is_mock": is_mock,
        }
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
