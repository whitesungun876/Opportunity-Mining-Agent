"""Badcase evaluation runner skeleton."""

from __future__ import annotations

from app.eval.metrics import compute_basic_metrics
from app.graph.main_graph import run_graph


def run_eval_case(topic: str) -> dict:
    """Run one mock eval case and return basic metrics."""
    state = run_graph(topic)
    return {"state": state, "metrics": compute_basic_metrics(state)}
