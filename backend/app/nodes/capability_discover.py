"""Capability discovery node."""

from __future__ import annotations

from app.fusion.capability_miner import discover_capabilities
from app.graph.state import GraphState


def capability_discover(state: GraphState) -> GraphState:
    capabilities = discover_capabilities(state)
    return {
        **state,
        "repo_capabilities": capabilities,
    }
