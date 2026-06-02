"""Ambiguous query graph behavior tests."""

from app.graph.main_graph import run_graph


def test_ambiguous_query_returns_refinement_without_cards():
    state = run_graph("agent")

    assert state["query_scope"]["scope"] == "ambiguous"
    assert state["refinement_required"] is True
    assert state["validated_cards"] == []
    assert state["opportunity_cards"] == []
    assert state["suggested_queries"]
    assert "Query Refinement Needed" in state["report_markdown"]
