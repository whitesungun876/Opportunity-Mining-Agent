"""Willingness-to-pay signal detection."""

from __future__ import annotations

from typing import Any

from app.commercial.schemas import WillingnessToPaySignal


SIGNAL_TERMS = {
    "enterprise_need": ["enterprise", "sso", "rbac", "audit", "security", "compliance", "permission"],
    "hosted_managed_need": ["hosted", "managed", "cloud", "dashboard", "support"],
    "production_blocker": ["production", "blocker", "blocked", "deployment", "scale", "latency", "performance"],
    "manual_workaround": ["workaround", "manual", "spreadsheet", "script", "internal", "homegrown"],
}


def _evidence_text(evidence: list[dict[str, Any]]) -> str:
    return " ".join(
        " ".join(str(item.get(key) or "") for key in ["title", "body", "labels"])
        for item in evidence
    ).lower()


def _related_evidence(card: dict[str, Any], evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence_ids = {str(item) for item in card.get("evidence_ids") or []}
    return [item for item in evidence_items if str(item.get("evidence_id")) in evidence_ids]


def detect_wtp_signal(card: dict[str, Any], evidence_items: list[dict[str, Any]]) -> dict[str, Any]:
    related = _related_evidence(card, evidence_items)
    evidence_ids = [str(item) for item in card.get("evidence_ids") or []]
    text = " ".join(
        [
            str(card.get("title") or ""),
            str(card.get("commercial_gap") or card.get("problem") or ""),
            str(card.get("pricing_hypothesis") or ""),
            _evidence_text(related),
        ]
    ).lower()
    matched: list[tuple[str, list[str]]] = []
    for signal_type, terms in SIGNAL_TERMS.items():
        hits = [term for term in terms if term in text]
        if hits:
            matched.append((signal_type, hits))
    comments = sum(int(item.get("comment_count") or 0) for item in related)
    if not matched:
        signal_type = "weak_signal"
        strength = "weak"
        reason = "No explicit enterprise, hosted, managed, security, support, or high-cost workaround signal was found."
    else:
        signal_type = matched[0][0]
        if len(matched) >= 2 and (comments >= 8 or len(evidence_ids) >= 5):
            strength = "strong"
        elif len(matched) >= 1 and (comments >= 3 or len(evidence_ids) >= 3):
            strength = "medium"
        else:
            strength = "weak"
        reason = f"Matched payment-hypothesis signals: {', '.join(hit for _, hits in matched for hit in hits[:3])}."
    summary = (
        "Payment hypothesis: evidence suggests a possible budgeted workflow pain, but willingness to pay still needs user validation."
        if strength != "weak"
        else "Payment hypothesis: current evidence proves pain more than budget urgency."
    )
    return WillingnessToPaySignal(
        opportunity_id=str(card.get("opportunity_id")),
        signal_type=signal_type,
        signal_summary=summary,
        strength=strength,  # type: ignore[arg-type]
        reason=reason,
        evidence_ids=evidence_ids,
    ).model_dump()


def detect_wtp_signals(cards: list[dict[str, Any]], evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [detect_wtp_signal(card, evidence_items) for card in cards]
