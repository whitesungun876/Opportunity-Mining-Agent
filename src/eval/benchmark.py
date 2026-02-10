"""Smoke tests and run-until-node helpers for repeatable evaluation."""

from __future__ import annotations

from typing import Any

# Fixture: minimal raw items for smoke and single-node tests (can live in data/ or tests/fixtures/)
SAMPLE_RAW_ITEMS = [
    {"content": "我们找不到好用的模板，导出又经常超时。"},
    {"content": "客服回复慢，工单经常丢。"},
]


def _merge_event(accumulated: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Merge one stream event into accumulated state. Handles node-keyed or flat updates."""
    if not event:
        return accumulated
    # LangGraph may yield {node_name: state_update} or flat state_update
    if len(event) == 1:
        key = next(iter(event))
        val = event[key]
        if isinstance(val, dict) and not isinstance(val.get("topic"), type(key)):
            return {**accumulated, **val}
    return {**accumulated, **event}


def run_smoke(state_input: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run the full graph with sample data; returns merged final state."""
    from src.graph import build_graph

    initial = state_input or {
        "topic": "smoke test",
        "raw_items": SAMPLE_RAW_ITEMS,
    }
    graph = build_graph()
    accumulated: dict[str, Any] = {}
    for event in graph.stream(initial):
        if isinstance(event, dict):
            accumulated = _merge_event(accumulated, event)
    return accumulated


def run_smoke_until(
    state_input: dict[str, Any],
    until_node: str,
) -> dict[str, Any]:
    """
    Run the graph from the given initial state and return state after `until_node` has run.
    Use for single-node regression: e.g. run_smoke_until(initial, "clean") then assert on state.
    """
    from src.graph import build_graph

    graph = build_graph()
    accumulated: dict[str, Any] = {}
    for event in graph.stream(state_input):
        if isinstance(event, dict):
            for node_name, update in event.items():
                if isinstance(update, dict):
                    accumulated = {**accumulated, **update}
                if node_name == until_node:
                    return accumulated
    return accumulated
