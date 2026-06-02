"""Adaptive query expansion tests."""

from app.search.expansion import AdaptiveQueryExpander
from app.search.planner import generate_search_plan


def test_adaptive_query_expand_adds_queries_when_evidence_is_weak():
    plan = generate_search_plan("MCP tools")
    expanded, reason = AdaptiveQueryExpander().expand(
        plan,
        {"evidence_count": 2, "repo_count": 1, "strong_evidence_count": 0, "iteration_count": 0},
    )

    assert len(expanded.global_issue_queries) >= len(plan.global_issue_queries)
    assert expanded.expansion_budget == plan.expansion_budget - 1
    assert "expanded for" in reason


def test_adaptive_query_expand_stops_when_budget_exhausted():
    plan = generate_search_plan("MCP tools")
    plan.expansion_budget = 0

    expanded, reason = AdaptiveQueryExpander().expand(
        plan,
        {"evidence_count": 0, "repo_count": 0, "strong_evidence_count": 0},
    )

    assert expanded.expansion_budget == 0
    assert reason == "expansion_budget exhausted"
