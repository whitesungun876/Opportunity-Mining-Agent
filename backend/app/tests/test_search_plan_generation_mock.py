"""Mock-mode SearchPlan generation tests."""

from app.search.intent import detect_intent_rules
from app.search.planner import generate_search_plan


def test_search_plan_generation_mock_has_required_query_sets():
    intent = detect_intent_rules("MCP tools")
    plan = generate_search_plan("MCP tools", intent)

    assert plan.intent == "technology"
    assert plan.repo_search_queries
    assert plan.global_issue_queries
    assert plan.positive_signals
    assert plan.negative_signals
    assert len(plan.repo_search_queries) <= 8
    assert len(plan.global_issue_queries) <= 16


def test_search_plan_generation_for_arbitrary_topic():
    plan = generate_search_plan("vector database")

    assert plan.topic == "vector database"
    assert any("vector database" in query for query in plan.repo_search_queries)
    assert any("vector database" in query for query in plan.global_issue_queries)


def test_search_plan_expands_mcp_auth_into_security_terms():
    plan = generate_search_plan("MCP auth and permissions")
    joined = " | ".join(plan.synonyms + plan.global_issue_queries).lower()

    assert "mcp authentication" in joined
    assert "mcp authorization" in joined
    assert "mcp access control" in joined
    assert "model context protocol security" in joined


def test_search_plan_expands_agent_framework_into_operational_terms():
    plan = generate_search_plan("AI agent framework")
    joined = " | ".join(plan.synonyms + plan.global_issue_queries).lower()

    assert "llm agent framework" in joined
    assert "agent orchestration" in joined
    assert "agent memory persistence" in joined
    assert "agent tracing" in joined


def test_search_plan_filters_low_information_terms():
    plan = generate_search_plan("security and compliance tools")

    assert "and" not in plan.seed_terms
    assert "tools" not in plan.seed_terms
    assert not any(query.startswith("and ") for query in plan.repo_search_queries)
    assert not any(query.startswith("tools ") for query in plan.repo_search_queries)


def test_search_plan_translates_commercial_terms_to_github_issue_language():
    plan = generate_search_plan("security and compliance tools")
    joined = " | ".join(plan.synonyms + plan.global_issue_queries).lower()

    assert "sso" in joined
    assert "rbac" in joined
    assert "audit logs" in joined
    assert "soc2" in joined
    assert "permission model" in joined
