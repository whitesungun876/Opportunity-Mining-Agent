"""Low-signal diagnostics tests."""

from pathlib import Path

from app.nodes.signal_diagnostics import diagnose_signal


def test_signal_diagnostics_repo_search_low():
    diagnostics = diagnose_signal({"selected_repos": [], "raw_issues": [], "evidence_items": []})

    assert diagnostics.low_signal_stage == "repo_search"
    assert "broaden_topic" in diagnostics.suggested_recovery_actions


def test_signal_diagnostics_issue_collect_low():
    diagnostics = diagnose_signal(
        {
            "selected_repos": [{"full_name": "owner/repo"}],
            "raw_issues": [{"id": idx} for idx in range(4)],
            "evidence_items": [{"evidence_id": f"ev_{idx}", "repo_owner": "owner", "repo_name": "repo"} for idx in range(4)],
        }
    )

    assert diagnostics.low_signal_stage == "issue_collect"
    assert "include_discussions" in diagnostics.suggested_recovery_actions


def test_signal_diagnostics_classifier_low():
    diagnostics = diagnose_signal(
        {
            "selected_repos": [{"full_name": "owner/repo"}],
            "raw_issues": [{"id": idx} for idx in range(20)],
            "evidence_items": [{"evidence_id": f"ev_{idx}", "repo_owner": "owner", "repo_name": "repo"} for idx in range(20)],
            "ranked_evidence_items": [{"evidence_id": f"ev_{idx}"} for idx in range(12)],
            "classified_issues": [{"issue_id": f"ev_{idx}", "value_level": "low_value"} for idx in range(12)],
            "high_value_issues": [{"issue_id": "ev_1"}],
            "low_value_issues": [{"issue_id": f"ev_{idx}"} for idx in range(11)],
        }
    )

    assert diagnostics.low_signal_stage == "issue_classify"
    assert "include_workflow_friction" in diagnostics.suggested_recovery_actions


def test_signal_diagnostics_validator_low():
    diagnostics = diagnose_signal(
        {
            "selected_repos": [{"full_name": "owner/repo"}],
            "raw_issues": [{"id": idx} for idx in range(20)],
            "evidence_items": [
                {"evidence_id": f"ev_{idx}", "repo_owner": "owner", "repo_name": f"repo-{idx % 4}"}
                for idx in range(20)
            ],
            "ranked_evidence_items": [{"evidence_id": f"ev_{idx}"} for idx in range(12)],
            "classified_issues": [{"issue_id": f"ev_{idx}", "value_level": "high_value"} for idx in range(8)],
            "high_value_issues": [{"issue_id": f"ev_{idx}"} for idx in range(8)],
            "pain_points": [{"pain_id": f"pain_{idx}"} for idx in range(5)],
            "pain_clusters": [{"cluster_id": "cluster_1"}],
            "commercial_gaps": [{"gap_id": "gap_1"}],
            "opportunity_cards": [{"opportunity_id": "opp_1"}],
            "validated_cards": [],
            "rejected_cards": [{"opportunity_id": "opp_1"}],
        }
    )

    assert diagnostics.low_signal_stage == "evidence_validate"
    assert "show_weak_signals" in diagnostics.suggested_recovery_actions


def test_low_signal_evidence_scattered():
    diagnostics = diagnose_signal(
        {
            "selected_repos": [{"full_name": f"owner/repo-{idx}"} for idx in range(5)],
            "raw_issues": [{"id": idx} for idx in range(80)],
            "evidence_items": [
                {"evidence_id": f"ev_{idx}", "repo_owner": "owner", "repo_name": f"repo-{idx % 8}"}
                for idx in range(80)
            ],
            "ranked_evidence_items": [{"evidence_id": f"ev_{idx}"} for idx in range(60)],
            "classified_issues": [{"issue_id": f"ev_{idx}", "value_level": "high_value"} for idx in range(40)],
            "high_value_issues": [{"issue_id": f"ev_{idx}"} for idx in range(30)],
            "pain_points": [{"pain_id": f"pain_{idx}"} for idx in range(30)],
            "pain_clusters": [],
            "rejected_pain_clusters": [
                {"cluster_id": f"cluster_{idx}", "theme": f"workflow {idx}", "evidence_count": 2}
                for idx in range(20)
            ],
            "opportunity_cards": [],
            "validated_cards": [],
        }
    )

    assert diagnostics.low_signal_type == "evidence_scattered"
    assert diagnostics.low_signal_stage == "cluster"
    assert diagnostics.pain_clusters_count == 20
    assert diagnostics.filtered_pain_clusters_count == 20
    assert diagnostics.low_signal_reason == (
        "Evidence was found, but signals were spread across too many pain clusters to validate a focused opportunity."
    )


def test_evidence_scattered_does_not_suggest_broaden():
    diagnostics = diagnose_signal(
        {
            "selected_repos": [{"full_name": "owner/repo"}],
            "raw_issues": [{"id": idx} for idx in range(80)],
            "evidence_items": [
                {"evidence_id": f"ev_{idx}", "repo_owner": "owner", "repo_name": f"repo-{idx % 8}"}
                for idx in range(80)
            ],
            "ranked_evidence_items": [{"evidence_id": f"ev_{idx}"} for idx in range(60)],
            "high_value_issues": [{"issue_id": f"ev_{idx}"} for idx in range(30)],
            "pain_points": [{"pain_id": f"pain_{idx}"} for idx in range(30)],
            "rejected_pain_clusters": [{"cluster_id": f"cluster_{idx}"} for idx in range(10)],
            "validated_cards": [],
        }
    )

    assert "broaden_topic" not in diagnostics.suggested_recovery_actions
    assert "narrow_to_cluster" in diagnostics.suggested_recovery_actions
    assert "try_focused_query" in diagnostics.suggested_recovery_actions


def test_frontend_low_signal_message_not_generic():
    source = Path(__file__).parents[3] / "frontend" / "components" / "TopicInput.tsx"
    text = source.read_text()

    assert "Not enough validated evidence yet" in text
    assert 'return "Low signal";' not in text


def test_frontend_scattered_signal_message():
    source = Path(__file__).parents[3] / "frontend" / "components" / "RunDetailDashboard.tsx"
    text = source.read_text()

    assert "Many signals found, but they are too scattered to validate a strong opportunity." in text
    assert "Choose a pain cluster to investigate" in text
    assert "Try focusing on one workflow." in text
    assert "const base = String(state?.canonical_topic" not in text
