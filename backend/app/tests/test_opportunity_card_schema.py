"""Opportunity card schema parsing tests."""

from app.nodes.opportunity_generate import parse_opportunity_card_response


def test_parse_opportunity_card_response_marks_strong_card():
    gap = {
        "gap_id": "gap_1",
        "theme": "Hosted evaluation workflow",
        "evidence_ids": ["ev1", "ev2", "ev3"],
        "migration_cost": "medium",
        "best_product_form": "Hosted SaaS",
    }
    state = {
        "evidence_items": [
            {"evidence_id": "ev1", "repo_owner": "o", "repo_name": "r", "author_login": "alice"},
            {"evidence_id": "ev2", "repo_owner": "o", "repo_name": "r", "author_login": "bob"},
            {"evidence_id": "ev3", "repo_owner": "o2", "repo_name": "r2", "author_login": "alice"},
        ]
    }
    response = {
        "opportunity_id": "opp_1",
        "title": "Hosted RAG Evaluation Dashboard",
        "target_user": "AI platform teams",
        "commercial_gap": "Need hosted badcase replay.",
        "migration_cost": "medium",
        "product_form": "Hosted SaaS",
        "pricing_hypothesis": "Hypothesis: teams may pay for hosted eval workflows.",
        "evidence_ids": ["ev1", "ev2", "ev3"],
        "score_json": {"overall": 75},
    }

    card = parse_opportunity_card_response(response, gap, state)

    assert card["opportunity_id"] == "opp_1"
    assert card["product_form"] == "Hosted SaaS"
    assert card["best_product_form"] == "Hosted SaaS"
    assert card["weak_card"] is False
    assert card["evidence_ids"] == ["ev1", "ev2", "ev3"]
    assert "o/r" in card["source_repos"]
    assert "alice" in card["first_users"]


def test_parse_opportunity_card_response_marks_weak_card_under_three_evidence():
    gap = {"gap_id": "gap_2", "evidence_ids": ["ev1", "ev2"], "migration_cost": "low"}
    card = parse_opportunity_card_response({"evidence_ids": ["ev1", "ev2"], "pricing_hypothesis": "Teams pay $99"}, gap)

    assert card["weak_card"] is True
    assert card["evidence_ids"] == ["ev1", "ev2"]
    assert card["pricing_hypothesis"].lower().startswith("hypothesis:")
