"""Fusion candidate validation node."""

from __future__ import annotations

from app.fusion.fusion_validator import validate_fusion_candidates
from app.graph.state import GraphState


def fusion_validate(state: GraphState) -> GraphState:
    validated, rejected = validate_fusion_candidates(state.get("fusion_candidates") or [], state)
    return {
        **state,
        "validated_fusion_candidates": validated,
        "rejected_fusion_candidates": rejected,
    }
