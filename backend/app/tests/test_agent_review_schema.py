"""Agent review schema parsing tests."""

from app.nodes.debate import parse_agent_review_response


def test_parse_agent_review_response_normalizes_schema():
    card = {"opportunity_id": "opp_1"}
    response = {
        "opportunity_id": "opp_1",
        "agent": "PM",
        "score": 8,
        "key_argument": "Clear production workflow pain.",
        "main_risk": "MVP scope may sprawl.",
        "recommendation": "validate",
    }

    review = parse_agent_review_response(response, card, "PM")

    assert review["opportunity_id"] == "opp_1"
    assert review["agent"] == "PM"
    assert review["score"] == 8
    assert review["recommendation"] == "validate"
    assert set(review) == {
        "opportunity_id",
        "agent",
        "score",
        "key_argument",
        "main_risk",
        "recommendation",
    }


def test_parse_agent_review_response_clamps_score_and_recommendation():
    card = {"opportunity_id": "opp_2"}
    review = parse_agent_review_response({"score": 99, "recommendation": "maybe"}, card, "Skeptic")

    assert review["score"] == 10
    assert review["recommendation"] == "watch"
    assert review["opportunity_id"] == "opp_2"


def test_parse_agent_review_response_forces_current_opportunity_id():
    card = {"opportunity_id": "opp_current"}
    review = parse_agent_review_response(
        {
            "opportunity_id": "opp_wrong",
            "score": 7,
            "recommendation": "build",
            "key_argument": "Supported by the card.",
            "main_risk": "Evidence may still be thin.",
        },
        card,
        "Engineer",
    )

    assert review["opportunity_id"] == "opp_current"
