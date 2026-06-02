"""Real report template should include evidence links."""

from app.nodes.report_write import _render_real_report


def test_report_template_contains_evidence_links():
    state = {
        "canonical_topic": "RAG evaluation",
        "selected_repos": [{"full_name": "o/r"}],
        "evidence_items": [
            {
                "evidence_id": "ev1",
                "source_url": "https://github.com/o/r/issues/1",
                "title": "Need eval workflow",
            },
            {
                "evidence_id": "ev2",
                "source_url": "https://github.com/o/r/issues/2",
                "title": "Need traces",
            },
            {
                "evidence_id": "ev3",
                "source_url": "https://github.com/o/r/issues/3",
                "title": "Need dashboard",
            },
        ],
        "high_value_issues": [1, 2, 3],
        "pain_points": [1, 2, 3],
        "validated_cards": [
            {
                "opportunity_id": "opp_1",
                "title": "Hosted RAG Eval",
                "target_user": "AI teams",
                "pain_summary": "Teams need eval workflows.",
                "commercial_gap": "Hosted dashboard gap.",
                "pricing_hypothesis": "Hypothesis: teams may pay.",
                "evidence_ids": ["ev1", "ev2", "ev3"],
                "validation_actions": ["Contact issue authors."],
                "risks": ["May be feature not product."],
            }
        ],
        "agent_reviews": [
            {
                "opportunity_id": "opp_1",
                "agent": "PM",
                "score": 8,
                "recommendation": "validate",
                "key_argument": "Clear pain.",
                "main_risk": "Scope.",
            }
        ],
        "final_decisions": [
            {
                "opportunity_id": "opp_1",
                "decision": "validate",
                "score": 78,
                "best_product_form": "Hosted SaaS",
                "migration_cost": "medium",
                "first_validation_action": "Contact 10 issue authors.",
                "top_risks": ["Competition"],
            }
        ],
        "errors": [],
    }

    markdown = _render_real_report(state)

    assert "https://github.com/o/r/issues/1" in markdown
    assert "Hosted RAG Eval" in markdown
    assert "## Run Summary" in markdown
    assert "Agent Reviews" in markdown
    assert "This report is rendered from validated cards" in markdown
