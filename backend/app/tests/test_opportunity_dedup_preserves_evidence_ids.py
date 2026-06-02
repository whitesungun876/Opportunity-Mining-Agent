"""Opportunity dedup must preserve evidence ids."""

from app.nodes.opportunity_dedup import dedupe_opportunities


def test_opportunity_dedup_preserves_evidence_ids():
    cards = [
        {
            "opportunity_id": "opp_1",
            "title": "Enterprise Auth Plugin",
            "pain_summary": "Teams need enterprise auth",
            "commercial_gap": "Plugin gap",
            "evidence_ids": ["ev1", "ev2", "ev3"],
            "score_json": {"overall": 50},
        },
        {
            "opportunity_id": "opp_2",
            "title": "Enterprise Auth Plugin",
            "pain_summary": "Teams need enterprise auth",
            "commercial_gap": "Plugin gap",
            "evidence_ids": ["ev3", "ev4", "ev5"],
            "score_json": {"overall": 80},
        },
    ]

    deduped = dedupe_opportunities(cards)

    assert len(deduped) == 1
    assert set(deduped[0]["evidence_ids"]) == {"ev1", "ev2", "ev3", "ev4", "ev5"}
    assert deduped[0]["opportunity_id"] == "opp_2"
