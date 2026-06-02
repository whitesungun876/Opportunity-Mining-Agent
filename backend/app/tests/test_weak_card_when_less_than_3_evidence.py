"""Weak card rule tests."""

from app.nodes.opportunity_generate import parse_opportunity_card_response


def test_weak_card_when_less_than_3_evidence():
    gap = {"gap_id": "gap_weak", "evidence_ids": ["ev1"], "migration_cost": "medium"}
    card = parse_opportunity_card_response({"evidence_ids": ["ev1"]}, gap)

    assert card["weak_card"] is True
    assert len(card["evidence_ids"]) == 1
