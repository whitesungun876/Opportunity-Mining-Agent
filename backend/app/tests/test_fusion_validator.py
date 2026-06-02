"""Fusion validator tests."""

from app.fusion.fusion_validator import validate_fusion_candidate


def _candidate(**overrides):
    base = {
        "fusion_id": "fusion_001",
        "title": "Production Debugging Layer",
        "fusion_thesis": "Tracing capability can be productized around a GitHub pain.",
        "why_combination_makes_sense": "GitHub evidence shows pain and the repo shows a mature capability.",
        "product_angle": "Hosted debugging dashboard",
        "evidence_ids": ["ev_001"],
        "repo_ids": ["langfuse/langfuse"],
        "paper_ids": ["paper_001"],
        "overall_score": 0.7,
        "research_evidence": [{"paper_id": "paper_001", "claim_summary": "Trace methods support technical feasibility."}],
    }
    base.update(overrides)
    return base


def test_fusion_validator_accepts_grounded_candidate():
    checked = validate_fusion_candidate(
        _candidate(),
        {"evidence_items": [{"evidence_id": "ev_001"}]},
    )

    assert checked["validation"]["is_valid"] is True


def test_fusion_validator_rejects_paper_as_market_proof():
    checked = validate_fusion_candidate(
        _candidate(fusion_thesis="Research proves willingness to pay is proven for this market."),
        {"evidence_items": [{"evidence_id": "ev_001"}]},
    )

    assert checked["validation"]["is_valid"] is False
    assert any("willingness to pay" in reason for reason in checked["validation"]["rejection_reasons"])


def test_fusion_validator_rejects_missing_repo_capability():
    checked = validate_fusion_candidate(_candidate(repo_ids=[]))

    assert checked["validation"]["is_valid"] is False
    assert any("source repo" in reason for reason in checked["validation"]["rejection_reasons"])
