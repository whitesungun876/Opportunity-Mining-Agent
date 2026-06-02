"""Opportunity scoring helpers."""

from __future__ import annotations


def score_card(card: dict) -> float:
    """Simple deterministic score based on evidence and migration cost."""
    evidence_score = min(50, len(card.get("evidence_ids", [])) * 10)
    cost_bonus = {"low": 30, "medium": 18, "high": 5}.get(card.get("migration_cost"), 10)
    return float(min(100, evidence_score + cost_bonus + 12))
