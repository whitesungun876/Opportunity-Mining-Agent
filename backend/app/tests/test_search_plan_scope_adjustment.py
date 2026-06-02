"""SearchPlan scope behavior tests."""

from app.search.intent import detect_intent_rules
from app.search.planner import generate_search_plan
from app.search.scope import detect_query_scope_rules


def test_search_plan_broad_uses_exploration_budget():
    scope = detect_query_scope_rules("AI agent framework")
    intent = detect_intent_rules(scope.normalized_query)
    plan = generate_search_plan(scope.normalized_query, intent, scope)

    assert plan.query_scope == "broad"
    assert plan.max_repos >= 10
    assert plan.expansion_budget >= 3
    assert plan.diversity_target >= 5
    assert plan.repo_search_queries
    assert plan.global_issue_queries


def test_search_plan_focused_uses_precision_budget():
    scope = detect_query_scope_rules("AI agent framework observability for production debugging")
    intent = detect_intent_rules(scope.normalized_query)
    plan = generate_search_plan(scope.normalized_query, intent, scope)

    assert plan.query_scope == "focused"
    assert plan.max_repos <= 6
    assert plan.expansion_budget == 2
    assert plan.precision_target >= 0.8


def test_search_plan_repo_specific_skips_broad_repo_search():
    scope = detect_query_scope_rules("langfuse/langfuse")
    intent = detect_intent_rules(scope.normalized_query)
    plan = generate_search_plan(scope.normalized_query, intent, scope)

    assert plan.query_scope == "repo_specific"
    assert plan.intent == "repo"
    assert plan.repo_hints == ["langfuse/langfuse"]
    assert plan.repo_search_queries == ["langfuse/langfuse"]
    assert all(query.startswith("repo:langfuse/langfuse") for query in plan.global_issue_queries)
    assert plan.max_repos == 1


def test_search_plan_ambiguous_requires_refinement_and_no_queries():
    scope = detect_query_scope_rules("agent")
    intent = detect_intent_rules(scope.normalized_query)
    plan = generate_search_plan(scope.normalized_query, intent, scope)

    assert plan.query_scope == "ambiguous"
    assert plan.refinement_required is True
    assert plan.suggested_queries
    assert plan.repo_search_queries == []
    assert plan.global_issue_queries == []
