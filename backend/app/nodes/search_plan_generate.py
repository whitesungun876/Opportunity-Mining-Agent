"""SearchPlan generation node."""

from __future__ import annotations

from app.graph.state import GraphState
from app.search.schemas import QueryScopeDetection, SearchIntent, SearchPlan
from app.search.planner import generate_search_plan


def _dedupe(items: list[str]) -> list[str]:
    return [item for item in dict.fromkeys(str(item).strip() for item in items if str(item).strip())]


def _apply_benchmark_profile(plan: SearchPlan, state: GraphState) -> SearchPlan:
    """Inject fixed eval benchmark issue queries without changing product planner code."""
    profile = state.get("benchmark_profile") or {}
    benchmark_queries = state.get("benchmark_queries") or profile.get("queries") or []
    if not benchmark_queries:
        return plan
    quality_keywords = state.get("benchmark_quality_keywords") or profile.get("quality_keywords") or []
    max_issues = state.get("benchmark_max_issues") or profile.get("default_max_issues") or plan.max_issues
    plan.global_issue_queries = _dedupe([str(query) for query in benchmark_queries])
    plan.max_issues = int(max_issues)
    plan.positive_signals = _dedupe([str(item) for item in quality_keywords] + plan.positive_signals)
    plan.source = "eval_profile"
    return plan


def search_plan_generate(state: GraphState) -> GraphState:
    if state.get("warm_start_evidence") and isinstance(state.get("search_plan"), dict):
        plan_dict = state.get("search_plan") or {}
        repo_queries = _dedupe([str(item) for item in plan_dict.get("repo_search_queries") or []])
        global_queries = _dedupe([str(item) for item in plan_dict.get("global_issue_queries") or []])
        return {
            **state,
            "repo_search_queries": repo_queries,
            "global_issue_queries": global_queries,
            "repo_issue_queries": _dedupe([str(item) for item in plan_dict.get("repo_issue_queries") or []]),
            "discussion_queries": _dedupe([str(item) for item in plan_dict.get("discussion_queries") or []]),
            "github_queries": _dedupe((state.get("github_queries") or []) + repo_queries + global_queries),
        }

    topic = (state.get("canonical_topic") or state.get("user_query") or "").strip()
    raw_intent = state.get("search_intent") or {}
    raw_scope = state.get("query_scope") or {}
    intent = SearchIntent(**raw_intent) if isinstance(raw_intent, dict) else None
    query_scope = QueryScopeDetection(**raw_scope) if isinstance(raw_scope, dict) and raw_scope else None
    plan = _apply_benchmark_profile(generate_search_plan(topic, intent, query_scope), state)
    plan_dict = plan.model_dump()
    github_queries = _dedupe(plan.repo_search_queries + plan.global_issue_queries)
    return {
        **state,
        "search_plan": plan_dict,
        "search_intent": (intent.model_dump() if intent else state.get("search_intent")),
        "repo_search_queries": plan.repo_search_queries,
        "global_issue_queries": plan.global_issue_queries,
        "repo_issue_queries": plan.repo_issue_queries,
        "discussion_queries": plan.discussion_queries,
        "github_queries": _dedupe((state.get("github_queries") or []) + github_queries),
    }
