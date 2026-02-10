"""SQLite / JSONL fallback storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def get_fallback_dir() -> Path:
    return Path("./data/runs").resolve()


def save_run_jsonl(run_id: str, events: list[dict[str, Any]]) -> None:
    """Write one run's event list to JSONL."""
    d = get_fallback_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{run_id}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")


def load_run_jsonl(run_id: str) -> list[dict[str, Any]]:
    """Load one run's events from JSONL."""
    path = get_fallback_dir() / f"{run_id}.jsonl"
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out
