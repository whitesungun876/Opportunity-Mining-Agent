"""Competitor alternative schema tests."""

from app.commercial.competitor_scan import scan_alternatives_for_card
from app.commercial.schemas import CompetitorAlternative


def test_competitor_alternative_schema():
    card = {"opportunity_id": "opp_1", "evidence_ids": ["ev_1"]}
    evidence = [
        {
            "evidence_id": "ev_1",
            "title": "Current workaround",
            "body": "We use Grafana and manual scripts today.",
            "source_url": "https://github.com/o/r/issues/1",
        }
    ]

    alternatives = [CompetitorAlternative(**item) for item in scan_alternatives_for_card(card, evidence)]

    assert alternatives
    assert alternatives[0].opportunity_id == "opp_1"
    assert alternatives[0].confidence > 0
