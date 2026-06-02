"""Opportunity deduplication tests."""

from app.nodes.opportunity_dedup import dedupe_opportunities


def test_opportunity_dedup_merges_duplicate_cards():
    cards = [
        {
            "opportunity_id": "opp_1",
            "title": "Hosted RAG Evaluation Dashboard",
            "pain_summary": "Teams need repeatable RAG evaluation",
            "commercial_gap": "Hosted dashboard gap",
            "evidence_ids": ["ev1", "ev2", "ev3"],
            "score_json": {"overall": 70},
        },
        {
            "opportunity_id": "opp_2",
            "title": "Hosted RAG Evaluation Dashboard",
            "pain_summary": "Teams need repeatable RAG evaluation",
            "commercial_gap": "Hosted dashboard gap",
            "evidence_ids": ["ev2", "ev3", "ev4"],
            "score_json": {"overall": 60},
        },
    ]

    deduped = dedupe_opportunities(cards)

    assert len(deduped) == 1
    assert set(deduped[0]["merged_from"]) == {"opp_1", "opp_2"}
