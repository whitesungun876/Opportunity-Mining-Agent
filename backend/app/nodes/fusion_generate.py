"""Fusion candidate generation node."""

from __future__ import annotations

from app.fusion.fusion_generator import generate_fusion_candidates
from app.graph.state import GraphState


def fusion_generate(state: GraphState) -> GraphState:
    candidates = generate_fusion_candidates(state)
    return {
        **state,
        "fusion_candidates": candidates,
    }
