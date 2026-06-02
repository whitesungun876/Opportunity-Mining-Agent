"""Buyer hypothesis schema tests."""

from app.commercial.buyer_hypothesis import build_buyer_hypothesis
from app.commercial.schemas import BuyerHypothesis


def test_buyer_hypothesis_schema():
    card = {
        "opportunity_id": "opp_1",
        "title": "Enterprise Permission Plugin",
        "target_user": "Platform teams adopting open-source tools",
        "evidence_ids": ["ev_1", "ev_2", "ev_3"],
    }

    hypothesis = BuyerHypothesis(**build_buyer_hypothesis(card))

    assert hypothesis.opportunity_id == "opp_1"
    assert hypothesis.evidence_ids == ["ev_1", "ev_2", "ev_3"]
    assert "Hypothesis:" in hypothesis.economic_buyer
    assert hypothesis.confidence > 0
