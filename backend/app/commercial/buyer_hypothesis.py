"""Buyer hypothesis generation."""

from __future__ import annotations

from typing import Any

from app.commercial.schemas import BuyerHypothesis


def _card_text(card: dict[str, Any]) -> str:
    return " ".join(
        str(card.get(key) or "")
        for key in ["title", "target_user", "pain_summary", "commercial_gap", "problem", "product_form", "best_product_form"]
    ).lower()


def _buyer_for(text: str) -> tuple[str, str, str]:
    if any(term in text for term in ["security", "compliance", "sso", "rbac", "permission", "audit"]):
        return "Security lead or Head of Engineering", "security and compliance tooling budget", "security or access-control review blocks adoption"
    if any(term in text for term in ["deployment", "self-host", "kubernetes", "devops", "infrastructure"]):
        return "DevOps lead or Head of Infrastructure", "infrastructure or platform engineering budget", "production deployment complexity creates recurring engineering cost"
    if any(term in text for term in ["rag", "llm", "agent", "evaluation", "trace", "debug", "observability"]):
        return "AI platform lead or Head of Engineering", "AI platform or developer productivity budget", "production AI workflow quality or debugging becomes a release blocker"
    return "CTO or Head of Engineering", "engineering productivity budget", "open-source adoption creates repeated production workflow friction"


def build_buyer_hypothesis(card: dict[str, Any]) -> dict[str, Any]:
    evidence_ids = [str(item) for item in card.get("evidence_ids") or []]
    text = _card_text(card)
    economic_buyer, budget_source, buying_trigger = _buyer_for(text)
    end_user = str(card.get("target_user") or "Engineering teams using the open-source project in production")
    confidence = min(0.85, 0.35 + len(evidence_ids) * 0.08)
    hypothesis = BuyerHypothesis(
        opportunity_id=str(card.get("opportunity_id")),
        end_user=f"Hypothesis: {end_user}",
        economic_buyer=f"Hypothesis: {economic_buyer}",
        buyer_persona=f"Hypothesis: {economic_buyer} buying for {end_user}",
        budget_source=f"Hypothesis: {budget_source}",
        buying_trigger=f"Hypothesis: {buying_trigger}",
        confidence=round(confidence, 3),
        evidence_ids=evidence_ids,
    )
    return hypothesis.model_dump()


def build_buyer_hypotheses(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [build_buyer_hypothesis(card) for card in cards]
