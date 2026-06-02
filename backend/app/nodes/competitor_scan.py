"""Lightweight competitor and alternative scan node."""

from __future__ import annotations

from app.commercial.competitor_scan import scan_alternatives
from app.graph.state import GraphState


def competitor_scan(state: GraphState) -> GraphState:
    cards = state.get("validated_cards") or []
    evidence_items = state.get("evidence_items") or []
    return {**state, "competitor_alternatives": scan_alternatives(cards, evidence_items)}
