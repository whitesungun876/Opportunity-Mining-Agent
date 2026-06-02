"""Outreach target generation node."""

from __future__ import annotations

from app.commercial.outreach_targets import build_outreach_targets
from app.graph.state import GraphState


def outreach_targets(state: GraphState) -> GraphState:
    cards = state.get("validated_cards") or []
    return {
        **state,
        "outreach_targets": build_outreach_targets(
            cards,
            state.get("evidence_items") or [],
            state.get("pain_points") or [],
        ),
    }
