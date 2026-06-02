"""SearchPlan schema tests."""

from app.search.schemas import SearchPlan


def test_search_plan_schema_minimum_fields():
    plan = SearchPlan(topic="MCP tools", intent="technology")

    assert plan.topic == "MCP tools"
    assert plan.intent == "technology"
    assert plan.seed_terms == []
    assert plan.max_repos == 8
    assert plan.max_issues == 80
    assert plan.expansion_budget == 2
