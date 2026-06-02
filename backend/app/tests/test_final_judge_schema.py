"""Final judge schema parsing tests."""

from app.nodes.final_judge import final_judge, parse_final_judge_response


def test_parse_final_judge_response_normalizes_schema():
    card = {"opportunity_id": "opp_1", "migration_cost": "medium", "best_product_form": "Hosted SaaS"}
    response = {
        "opportunity_id": "opp_1",
        "decision": "validate",
        "score": 78,
        "best_product_form": "Hosted SaaS",
        "migration_cost": "medium",
        "reason": "Good evidence, validate first.",
        "top_risks": ["Competition"],
        "first_validation_action": "Contact 10 issue authors this week.",
        "decision_confidence": 0.74,
    }

    decision = parse_final_judge_response(response, card)

    assert decision["opportunity_id"] == "opp_1"
    assert decision["decision"] == "validate"
    assert decision["score"] == 78
    assert decision["top_risks"] == ["Competition"]
    assert decision["decision_confidence"] == 0.74
    assert set(decision) == {
        "opportunity_id",
        "decision",
        "score",
        "best_product_form",
        "migration_cost",
        "reason",
        "top_risks",
        "first_validation_action",
        "decision_confidence",
    }


def test_parse_final_judge_response_defaults_invalid_values():
    card = {"opportunity_id": "opp_2", "migration_cost": "low"}
    decision = parse_final_judge_response({"decision": "maybe", "score": 999}, card)

    assert decision["decision"] == "watch"
    assert decision["score"] == 100
    assert decision["migration_cost"] == "low"


def test_parse_final_judge_response_forces_current_opportunity_id():
    card = {"opportunity_id": "opp_current", "migration_cost": "medium"}
    decision = parse_final_judge_response(
        {
            "opportunity_id": "opp_wrong",
            "decision": "build",
            "score": 81,
            "migration_cost": "medium",
        },
        card,
    )

    assert decision["opportunity_id"] == "opp_current"


def test_final_judge_returns_empty_when_no_validated_cards():
    state = final_judge({"validated_cards": [], "final_decisions": [{"opportunity_id": "opp_1"}], "errors": []})

    assert state["final_decisions"] == []
    assert state["errors"] == []
