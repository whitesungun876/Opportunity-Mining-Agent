"""Report commercial validation tests."""

from app.nodes.report_write import _render_real_report


def test_report_contains_commercial_validation():
    state = {
        "evidence_items": [
            {
                "evidence_id": "ev_1",
                "source_url": "https://github.com/o/r/issues/1",
                "title": "Need production dashboard",
            }
        ],
        "validated_cards": [
            {
                "opportunity_id": "opp_1",
                "title": "Hosted Production Dashboard",
                "target_user": "Platform teams",
                "pain_summary": "Teams need production visibility.",
                "commercial_gap": "Hosted dashboard gap.",
                "pricing_hypothesis": "Hypothesis: teams may pay after validation.",
                "evidence_ids": ["ev_1"],
                "validation_actions": ["Contact issue authors."],
            }
        ],
        "buyer_hypotheses": [
            {
                "opportunity_id": "opp_1",
                "end_user": "Hypothesis: platform teams",
                "economic_buyer": "Hypothesis: Head of Engineering",
                "budget_source": "Hypothesis: developer productivity budget",
                "buying_trigger": "Hypothesis: production blocker",
            }
        ],
        "wtp_signals": [
            {
                "opportunity_id": "opp_1",
                "strength": "medium",
                "signal_summary": "Payment hypothesis: possible budgeted workflow pain.",
                "reason": "Matched production blocker.",
            }
        ],
        "competitor_alternatives": [
            {
                "opportunity_id": "opp_1",
                "name": "Manual process",
                "limitation": "Slow",
                "confidence": 0.3,
                "source": "https://github.com/o/r/issues/1",
            }
        ],
        "outreach_targets": [
            {
                "opportunity_id": "opp_1",
                "github_user": "octocat",
                "source_repo": "o/r",
                "source_url": "https://github.com/o/r/issues/1",
                "outreach_angle": "Ask about workflow.",
            }
        ],
        "validation_plans": [
            {
                "opportunity_id": "opp_1",
                "seven_day_plan": ["Day 1: Contact 10 issue authors."],
            }
        ],
        "agent_reviews": [],
        "final_decisions": [{"opportunity_id": "opp_1", "decision": "validate", "score": 70}],
        "errors": [],
    }

    markdown = _render_real_report(state)

    assert "Buyer Hypothesis" in markdown
    assert "Willingness-to-Pay Signal" in markdown
    assert "Current Alternatives" in markdown
    assert "First Users to Contact" in markdown
    assert "7-Day Validation Plan" in markdown
