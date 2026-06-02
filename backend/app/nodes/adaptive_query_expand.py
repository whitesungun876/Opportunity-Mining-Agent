"""Adaptive query expansion node."""

from __future__ import annotations

from app.graph.state import GraphState
from app.search.expansion import AdaptiveQueryExpander
from app.search.schemas import SearchPlan


def _evidence_stats(state: GraphState) -> dict:
    ranked = state.get("ranked_evidence_items") or []
    repos = {
        str(item.get("repo") or f"{item.get('repo_owner')}/{item.get('repo_name')}")
        for item in ranked
    }
    strong = [
        item for item in ranked
        if float(item.get("evidence_quality_score") or 0) >= 8
    ]
    return {
        "evidence_count": len(ranked),
        "repo_count": len([repo for repo in repos if repo and repo != "/"]),
        "strong_evidence_count": len(strong),
        "iteration_count": state.get("iteration_count") or 0,
    }


def adaptive_query_expand(state: GraphState) -> GraphState:
    raw_plan = state.get("search_plan") or {}
    plan = SearchPlan(**raw_plan)
    stats = _evidence_stats(state)
    expanded, reason = AdaptiveQueryExpander().expand(plan, stats)
    iteration_count = (state.get("iteration_count") or 0) + 1
    expansion = {
        "iteration": iteration_count,
        "expansion_reason": reason,
        "before_query_count": len(plan.global_issue_queries),
        "after_query_count": len(expanded.global_issue_queries),
        "expansion_budget": expanded.expansion_budget,
    }
    return {
        **state,
        "search_plan": expanded.model_dump(),
        "repo_search_queries": expanded.repo_search_queries,
        "global_issue_queries": expanded.global_issue_queries,
        "repo_issue_queries": expanded.repo_issue_queries,
        "discussion_queries": expanded.discussion_queries,
        "query_expansions": (state.get("query_expansions") or []) + [expansion],
        "iteration_count": iteration_count,
    }
