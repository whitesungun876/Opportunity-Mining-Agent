"""Dynamic search planner tests."""

from app.nodes.query_rewrite import query_rewrite
from app.search.planner import build_search_plan, expand_search_plan


def test_build_search_plan_for_arbitrary_topic():
    plan = build_search_plan("vector database")

    assert plan.topic == "vector database"
    assert plan.intent == "technology"
    assert plan.repo_search_queries
    assert plan.global_issue_queries
    assert "production" in plan.positive_signals
    assert any("vector database" in query for query in plan.global_issue_queries)


def test_build_search_plan_detects_repo_intent():
    plan = build_search_plan("langfuse/langfuse")

    assert plan.intent == "repo"
    assert plan.repo_hints == ["langfuse/langfuse"]
    assert all(query.startswith("repo:langfuse/langfuse") for query in plan.global_issue_queries)


def test_expand_search_plan_adds_more_issue_queries():
    plan = build_search_plan("MCP tools")
    expanded = expand_search_plan(plan, iteration_count=1)

    assert len(expanded.global_issue_queries) > len(plan.global_issue_queries)
    assert expanded.expansion_budget < plan.expansion_budget


def test_eval_profile_injects_fixed_issue_queries_without_replacing_product_planner():
    state = query_rewrite(
        {
            "run_id": "test",
            "user_query": "RAG evaluation",
            "benchmark_queries": ['"RAG evaluation" production issue type:issue'],
            "benchmark_quality_keywords": ["regression"],
            "benchmark_max_issues": 12,
            "errors": [],
            "iteration_count": 2,
        }
    )

    plan = state["search_plan"]
    assert plan["source"] == "eval_profile"
    assert plan["global_issue_queries"] == ['"RAG evaluation" production issue type:issue']
    assert plan["repo_search_queries"]
    assert plan["max_issues"] == 12
    assert "regression" in plan["positive_signals"]
