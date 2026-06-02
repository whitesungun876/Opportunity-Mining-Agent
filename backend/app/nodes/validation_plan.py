"""Seven-day validation plan node."""

from __future__ import annotations

from app.commercial.validation_plan import build_validation_plans
from app.graph.state import GraphState


def validation_plan(state: GraphState) -> GraphState:
    cards = state.get("validated_cards") or []
    return {**state, "validation_plans": build_validation_plans(cards, state.get("wtp_signals") or [])}
