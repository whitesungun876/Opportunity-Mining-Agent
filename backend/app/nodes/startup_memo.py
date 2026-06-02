"""Startup memo node."""

from __future__ import annotations

from app.commercial.startup_memo import build_startup_memos
from app.graph.state import GraphState


def startup_memo(state: GraphState) -> GraphState:
    cards = state.get("validated_cards") or []
    return {
        **state,
        "startup_memos": build_startup_memos(
            cards,
            buyer_hypotheses=state.get("buyer_hypotheses") or [],
            wtp_signals=state.get("wtp_signals") or [],
            alternatives=state.get("competitor_alternatives") or [],
            outreach_targets=state.get("outreach_targets") or [],
            validation_plans=state.get("validation_plans") or [],
            final_decisions=state.get("final_decisions") or [],
        ),
    }
