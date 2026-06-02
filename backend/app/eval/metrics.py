"""Basic graph output metrics."""

from __future__ import annotations


def compute_basic_metrics(state: dict) -> dict[str, float | int]:
    cards = state.get("opportunity_cards") or []
    validated = state.get("validated_cards") or []
    evidence_counts = [len(card.get("evidence_ids", [])) for card in validated]
    return {
        "opportunity_count": len(cards),
        "validated_count": len(validated),
        "avg_evidence_per_card": sum(evidence_counts) / max(1, len(evidence_counts)),
        "high_value_issue_count": len(state.get("high_value_issues") or []),
    }
