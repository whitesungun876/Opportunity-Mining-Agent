"""Mock eval judges."""

from __future__ import annotations


def judge_smoke_quality(state: dict) -> dict:
    cards = state.get("validated_cards") or []
    passed = (
        len(cards) >= 3
        and all(len(card.get("evidence_ids", [])) >= 3 for card in cards)
        and bool(state.get("report_markdown"))
    )
    return {"passed": passed, "reason": "mock smoke quality gate"}
