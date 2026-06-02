"""Buyer hypothesis node."""

from __future__ import annotations

from app.commercial.buyer_hypothesis import build_buyer_hypotheses
from app.graph.state import GraphState


def buyer_hypothesis(state: GraphState) -> GraphState:
    cards = state.get("validated_cards") or []
    return {**state, "buyer_hypotheses": build_buyer_hypotheses(cards)}
