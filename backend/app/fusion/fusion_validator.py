"""Validation rules for cross-source fusion candidates."""

from __future__ import annotations

from typing import Any


UNSUPPORTED_MARKET_PHRASES = [
    "paper proves demand",
    "paper proves users will pay",
    "research proves willingness to pay",
    "willingness to pay is proven",
    "market is proven by the paper",
]


def validate_fusion_candidate(candidate: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate that fusion candidates are grounded and not over-claimed."""
    state = state or {}
    known_evidence = {str(item.get("evidence_id")) for item in state.get("evidence_items") or [] if item.get("evidence_id")}
    evidence_ids = [str(item) for item in candidate.get("evidence_ids") or []]
    repo_ids = [str(item) for item in candidate.get("repo_ids") or []]
    paper_ids = [str(item) for item in candidate.get("paper_ids") or []]
    combined_text = " ".join(
        str(candidate.get(key) or "")
        for key in ["title", "fusion_thesis", "why_combination_makes_sense", "product_angle"]
    ).lower()

    rejection_reasons: list[str] = []
    warnings: list[str] = []
    if not evidence_ids:
        rejection_reasons.append("Fusion candidate needs at least one GitHub pain evidence_id.")
    if known_evidence and not set(evidence_ids).intersection(known_evidence):
        rejection_reasons.append("Fusion candidate evidence_ids do not map to known GitHub evidence.")
    if not repo_ids:
        rejection_reasons.append("Fusion candidate needs at least one source repo capability.")
    for phrase in UNSUPPORTED_MARKET_PHRASES:
        if phrase in combined_text:
            rejection_reasons.append("Research evidence cannot be used as proof of willingness to pay or market demand.")
            break
    for paper in candidate.get("research_evidence") or []:
        claim = str(paper.get("claim_summary") or "").lower()
        if "willingness to pay" in claim or "users will pay" in claim:
            rejection_reasons.append("Research claim incorrectly asserts willingness to pay.")
            break
    if not paper_ids:
        warnings.append("No paper evidence attached; fusion relies on GitHub pain and repo capability only.")
    if float(candidate.get("overall_score") or 0) < 0.35:
        rejection_reasons.append("Fusion score is too weak for review.")

    is_valid = not rejection_reasons
    return {
        **candidate,
        "validation": {
            "is_valid": is_valid,
            "validation_status": "validated" if is_valid else "rejected",
            "rejection_reasons": rejection_reasons,
            "warnings": warnings,
        },
    }


def validate_fusion_candidates(candidates: list[dict[str, Any]], state: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    checked = [validate_fusion_candidate(candidate, state) for candidate in candidates]
    return (
        [candidate for candidate in checked if candidate["validation"]["is_valid"]],
        [candidate for candidate in checked if not candidate["validation"]["is_valid"]],
    )
