"""Small in-memory helpers for typed opportunity graphs."""

from __future__ import annotations

from typing import Any


class OpportunityGraphStore:
    """Query helper over serialized graph nodes and edges."""

    def __init__(self, graph: dict[str, Any]) -> None:
        self.graph = graph
        self.nodes = {str(node.get("node_id")): node for node in graph.get("nodes") or []}
        self.edges = graph.get("edges") or []

    def nodes_by_type(self, node_type: str) -> list[dict[str, Any]]:
        return [node for node in self.nodes.values() if node.get("node_type") == node_type]

    def outgoing(self, node_id: str, edge_type: str | None = None) -> list[dict[str, Any]]:
        return [
            edge
            for edge in self.edges
            if edge.get("source_id") == node_id and (edge_type is None or edge.get("edge_type") == edge_type)
        ]

    def incoming(self, node_id: str, edge_type: str | None = None) -> list[dict[str, Any]]:
        return [
            edge
            for edge in self.edges
            if edge.get("target_id") == node_id and (edge_type is None or edge.get("edge_type") == edge_type)
        ]
