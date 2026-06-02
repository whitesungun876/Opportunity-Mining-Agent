"""Build typed opportunity graph node."""

from __future__ import annotations

from app.fusion.graph_builder import build_opportunity_graph
from app.graph.state import GraphState


def evidence_graph_build(state: GraphState) -> GraphState:
    graph = build_opportunity_graph(state)
    return {
        **state,
        "opportunity_graph": graph,
        "graph_nodes": graph.get("nodes", []),
        "graph_edges": graph.get("edges", []),
    }
