"""Query rewrite node."""

from __future__ import annotations

from app.graph.state import GraphState
from app.search.expansion import expand_for_quality_gap
from app.search.planner import SearchPlan, build_search_plan


def _dedupe(items: list[str]) -> list[str]:
    return [item for item in dict.fromkeys(str(item).strip() for item in items if str(item).strip())]


def _apply_benchmark_profile(plan: SearchPlan, state: GraphState) -> SearchPlan:
    """Override dynamic issue queries with fixed eval profile queries when present."""
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


def query_rewrite(state: GraphState) -> GraphState:
    """Build a dynamic GitHub SearchPlan for an arbitrary user topic."""
    topic = (state.get("user_query") or state.get("canonical_topic") or "").strip()
    canonical_topic = topic or "GitHub developer tooling"
    plan = build_search_plan(canonical_topic, iteration_count=state.get("iteration_count") or 0)
    plan = _apply_benchmark_profile(plan, state)
    plan_dict = plan.model_dump()
    github_queries = list(
        dict.fromkeys(
            plan.repo_search_queries
            + plan.global_issue_queries
        )
    )
    return {
        **state,
        "canonical_topic": canonical_topic,
        "search_intent": {
            "intent": plan.intent,
            "normalized_topic": canonical_topic,
            "confidence": 0.65,
            "reason": "Compatibility query rewrite pass.",
        },
        "search_plan": plan_dict,
        "github_queries": list(dict.fromkeys((state.get("github_queries") or []) + github_queries)),
        "repo_search_queries": plan.repo_search_queries,
        "global_issue_queries": plan.global_issue_queries,
        "repo_issue_queries": plan.repo_issue_queries,
        "discussion_queries": plan.discussion_queries,
        "iteration_count": state.get("iteration_count") or 0,
        "errors": state.get("errors") or [],
    }


def expand_query(state: GraphState) -> GraphState:
    """Expand the dynamic SearchPlan when issue quality is not sufficient."""
    iteration_count = (state.get("iteration_count") or 0) + 1
    topic = state.get("canonical_topic") or state.get("user_query") or "developer tooling"
    existing_plan = state.get("search_plan") or {}
    if existing_plan:
        plan = expand_for_quality_gap(SearchPlan(**existing_plan), iteration_count=iteration_count)
    else:
        plan = build_search_plan(topic, iteration_count=iteration_count)
    plan = _apply_benchmark_profile(plan, state)
    plan_dict = plan.model_dump()
    github_queries = list(dict.fromkeys(plan.repo_search_queries + plan.global_issue_queries))
    return {
        **state,
        "search_intent": {
            "intent": plan.intent,
            "normalized_topic": topic,
            "confidence": 0.65,
            "reason": "Compatibility query expansion pass.",
        },
        "search_plan": plan_dict,
        "github_queries": list(dict.fromkeys((state.get("github_queries") or []) + github_queries)),
        "repo_search_queries": plan.repo_search_queries,
        "global_issue_queries": plan.global_issue_queries,
        "repo_issue_queries": plan.repo_issue_queries,
        "discussion_queries": plan.discussion_queries,
        "iteration_count": iteration_count,
    }
