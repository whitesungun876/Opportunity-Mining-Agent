"""Typed evidence graph builder tests."""

from app.fusion.graph_builder import build_opportunity_graph


def test_opportunity_graph_links_repo_pain_evidence_and_opportunity():
    state = {
        "evidence_items": [
            {
                "evidence_id": "ev_001",
                "repo_owner": "langfuse",
                "repo_name": "langfuse",
                "repo_url": "https://github.com/langfuse/langfuse",
                "source_url": "https://github.com/langfuse/langfuse/issues/1",
                "source_type": "issue",
                "title": "Need production trace replay",
            }
        ],
        "pain_points": [
            {
                "pain_id": "pain_001",
                "evidence_id": "ev_001",
                "pain_type": "observability_gap",
                "complaint": "Teams need production trace replay.",
            }
        ],
        "commercial_gaps": [
            {
                "gap_id": "gap_001",
                "commercial_gap_type": "Monitoring / evaluation dashboard gap",
                "evidence_ids": ["ev_001"],
            }
        ],
        "validated_cards": [
            {
                "opportunity_id": "opp_001",
                "title": "Hosted Trace Replay Dashboard",
                "evidence_ids": ["ev_001"],
            }
        ],
    }

    graph = build_opportunity_graph(state)
    node_types = {node["node_type"] for node in graph["nodes"]}
    edge_types = {edge["edge_type"] for edge in graph["edges"]}

    assert {"Repo", "Evidence", "PainPoint", "CommercialGap", "Opportunity"}.issubset(node_types)
    assert "repo_has_pain" in edge_types
    assert "pain_supported_by_evidence" in edge_types
    assert "pain_has_commercial_gap" in edge_types
    assert "opportunity_supported_by_evidence" in edge_types
