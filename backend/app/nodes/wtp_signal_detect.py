"""Willingness-to-pay signal detection node."""

from __future__ import annotations

from app.commercial.wtp_signal import detect_wtp_signals
from app.graph.state import GraphState


def wtp_signal_detect(state: GraphState) -> GraphState:
    cards = state.get("validated_cards") or []
    evidence_items = state.get("evidence_items") or []
    return {**state, "wtp_signals": detect_wtp_signals(cards, evidence_items)}
