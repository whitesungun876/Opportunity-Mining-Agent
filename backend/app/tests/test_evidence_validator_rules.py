"""Deterministic evidence validator rule tests."""

from app.nodes.evidence_validate import validate_card_deterministic


def test_validate_card_deterministic_accepts_grounded_hypothesis_card():
    evidence = {
        "ev1": {"source_url": "https://github.com/o/r/issues/1"},
        "ev2": {"source_url": "https://github.com/o/r/issues/2"},
        "ev3": {"source_url": "https://github.com/o/r/issues/3"},
    }
    card = {
        "opportunity_id": "opp_1",
        "evidence_ids": ["ev1", "ev2", "ev3"],
        "pricing_hypothesis": "Hypothesis: teams may pay for this if interviews confirm budget.",
    }

    out = validate_card_deterministic(card, evidence)

    assert out["validation"]["is_valid"] is True
    assert out["evidence_urls"] == [
        "https://github.com/o/r/issues/1",
        "https://github.com/o/r/issues/2",
        "https://github.com/o/r/issues/3",
    ]


def test_validate_card_deterministic_rejects_unsupported_pricing_fact():
    evidence = {
        "ev1": {"source_url": "https://github.com/o/r/issues/1"},
        "ev2": {"source_url": "https://github.com/o/r/issues/2"},
        "ev3": {"source_url": "https://github.com/o/r/issues/3"},
    }
    card = {
        "opportunity_id": "opp_2",
        "evidence_ids": ["ev1", "ev2", "ev3"],
        "pricing_hypothesis": "Teams will pay $99 per month.",
    }

    out = validate_card_deterministic(card, evidence)

    assert out["validation"]["is_valid"] is False
    assert out["validation"]["unsupported_claims"]


def test_validate_card_deterministic_strict_rejects_single_evidence_card():
    evidence = {"ev1": {"source_url": "https://github.com/o/r/issues/1"}}
    card = {
        "opportunity_id": "opp_3",
        "evidence_ids": ["ev1"],
        "pricing_hypothesis": "Hypothesis: teams may pay after validation interviews.",
    }

    out = validate_card_deterministic(card, evidence)

    assert out["validation"]["validation_mode"] == "strict"
    assert out["validation"]["is_valid"] is False
    assert out["validation"]["evidence_count"] == 1
    assert out["weak_card"] is True
    assert out["validation"]["rejection_reasons"]


def test_validate_card_deterministic_smoke_accepts_single_evidence_card_as_weak():
    evidence = {"ev1": {"source_url": "https://github.com/o/r/issues/1"}}
    card = {
        "opportunity_id": "opp_4",
        "evidence_ids": ["ev1"],
        "pricing_hypothesis": "Hypothesis: teams may pay after validation interviews.",
    }

    out = validate_card_deterministic(card, evidence, validation_mode="smoke")

    assert out["validation"]["validation_mode"] == "smoke"
    assert out["validation"]["is_valid"] is True
    assert out["validation"]["validation_status"] == "validated"
    assert out["validation"]["evidence_count"] == 1
    assert out["validation"]["evidence_urls_count"] == 1
    assert out["weak_card"] is True
    assert out["validation"]["rejection_reasons"] == []
