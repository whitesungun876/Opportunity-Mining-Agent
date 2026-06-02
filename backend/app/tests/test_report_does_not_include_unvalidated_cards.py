"""Report template must omit unvalidated cards and their decisions/reviews."""

from app.nodes.report_write import _render_real_report


def test_report_does_not_include_unvalidated_cards():
    state = {
        "evidence_items": [
            {
                "evidence_id": "ev1",
                "source_url": "https://github.com/o/r/issues/1",
                "title": "Validated issue",
            }
        ],
        "validated_cards": [
            {
                "opportunity_id": "opp_valid",
                "title": "Validated Opportunity",
                "target_user": "AI teams",
                "pain_summary": "A supported pain.",
                "commercial_gap": "A supported gap.",
                "evidence_ids": ["ev1"],
            }
        ],
        "opportunity_cards": [
            {"opportunity_id": "opp_rejected", "title": "Rejected Opportunity"},
        ],
        "rejected_cards": [
            {"opportunity_id": "opp_rejected", "title": "Rejected Opportunity"},
        ],
        "agent_reviews": [
            {
                "opportunity_id": "opp_valid",
                "agent": "PM",
                "score": 7,
                "recommendation": "validate",
                "key_argument": "Supported by evidence.",
                "main_risk": "Small sample.",
            },
            {
                "opportunity_id": "opp_rejected",
                "agent": "PM",
                "score": 2,
                "recommendation": "reject",
                "key_argument": "This should not render.",
                "main_risk": "This should not render.",
            },
        ],
        "final_decisions": [
            {
                "opportunity_id": "opp_valid",
                "decision": "validate",
                "score": 70,
                "best_product_form": "Plugin",
                "migration_cost": "low",
            },
            {
                "opportunity_id": "opp_rejected",
                "decision": "reject",
                "score": 20,
                "best_product_form": "Watch",
                "migration_cost": "high",
            },
        ],
        "errors": [],
    }

    markdown = _render_real_report(state)

    assert "Validated Opportunity" in markdown
    assert "https://github.com/o/r/issues/1" in markdown
    assert "Rejected Opportunity" not in markdown
    assert "This should not render" not in markdown
