"""Node-level observability: timing, I/O summary, and error logging."""

from __future__ import annotations

import json
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Callable

from src.utils.logger import get_logger

logger = get_logger(__name__)
_structured_logger = get_logger("src.utils.observability.structured")

_node_run_records: ContextVar[list[dict[str, Any]]] = ContextVar("node_run_records", default=[])


def _append_run_record(node_name: str, duration_ms: float, event: str) -> None:
    try:
        records = _node_run_records.get().copy()
        records.append({"node": node_name, "duration_ms": duration_ms, "event": event})
        _node_run_records.set(records)
    except LookupError:
        _node_run_records.set([{"node": node_name, "duration_ms": duration_ms, "event": event}])
    except Exception:
        pass


def get_node_run_records() -> list[dict[str, Any]]:
    """Return and clear the list of node run records for the current context (e.g. after a run)."""
    try:
        records = _node_run_records.get()
        _node_run_records.set([])
        return list(records)
    except LookupError:
        return []


def _state_keys_summary(state: dict[str, Any] | None) -> list[str]:
    """Return top-level keys that are present and non-None (for logging)."""
    if not state:
        return []
    return [k for k in state if state.get(k) is not None]


def wrap_node(node_name: str, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """
    Wrap a graph node to record duration, input/output key summary, and errors.
    Logs one structured line per run; on exception logs and re-raises.
    """

    def wrapped(state: dict[str, Any]) -> dict[str, Any]:
        in_keys = _state_keys_summary(state)
        start = time.perf_counter()
        ts = datetime.now(timezone.utc).isoformat()
        try:
            out = fn(state)
            duration_ms = (time.perf_counter() - start) * 1000
            out_keys = _state_keys_summary(out)
            new_keys = [k for k in out_keys if k not in set(in_keys)]
            payload = {
                "event": "node_finish",
                "ts": ts,
                "node": node_name,
                "duration_ms": round(duration_ms, 2),
                "in_keys": in_keys,
                "out_keys": out_keys,
                "new_keys": new_keys,
            }
            _structured_logger.info("%s", json.dumps(payload, ensure_ascii=False))
            _append_run_record(node_name, round(duration_ms, 2), "node_finish")
            logger.info(
                "node=%s duration_ms=%.2f new_keys=%s",
                node_name,
                duration_ms,
                new_keys if new_keys else "(none)",
            )
            return out
        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            payload = {
                "event": "node_error",
                "ts": ts,
                "node": node_name,
                "duration_ms": round(duration_ms, 2),
                "in_keys": in_keys,
                "error": str(e),
            }
            _structured_logger.warning("%s", json.dumps(payload, ensure_ascii=False))
            _append_run_record(node_name, round(duration_ms, 2), "node_error")
            logger.warning(
                "node=%s duration_ms=%.2f in_keys=%s error=%s",
                node_name,
                duration_ms,
                in_keys,
                str(e),
            )
            raise

    return wrapped
