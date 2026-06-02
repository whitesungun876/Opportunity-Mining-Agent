"""Fusion candidate scoring helpers."""

from __future__ import annotations

from typing import Any


def score_fusion_candidate(
    pain: dict[str, Any],
    capability: dict[str, Any],
    research: list[dict[str, Any]],
) -> dict[str, float]:
    severity = float(pain.get("severity") or 0.65)
    evidence_count = len(set([pain.get("evidence_id"), *(pain.get("evidence_ids") or []), *(capability.get("evidence_ids") or [])]) - {None, ""})
    maturity = float(capability.get("maturity_score") or 0.5)
    paper_support = max([float(item.get("confidence") or 0) for item in research] or [0.35])
    evidence_strength = min(1.0, 0.2 + evidence_count * 0.12)
    feasibility = min(1.0, maturity * 0.7 + paper_support * 0.3)
    novelty = 0.68 if research else 0.55
    commercial = min(1.0, severity * 0.45 + evidence_strength * 0.3 + maturity * 0.25)
    overall = (
        0.25 * severity
        + 0.2 * maturity
        + 0.15 * paper_support
        + 0.15 * commercial
        + 0.15 * feasibility
        + 0.1 * novelty
    )
    return {
        "novelty_score": round(novelty, 3),
        "feasibility_score": round(feasibility, 3),
        "evidence_strength": round(evidence_strength, 3),
        "commercial_potential": round(commercial, 3),
        "overall_score": round(min(1.0, overall), 3),
    }
