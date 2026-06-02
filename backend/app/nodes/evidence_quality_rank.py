"""Evidence quality ranking node."""

from __future__ import annotations

from app.graph.state import GraphState
from app.search.scorer import EvidenceQualityRanker


LLM_EVIDENCE_BUDGET_BY_SCOPE = {
    "repo_specific": 30,
    "focused": 45,
    "broad": 60,
    "ambiguous": 0,
}


def _llm_evidence_budget(plan: dict, max_issues: int) -> int:
    scope = str(plan.get("query_scope") or "")
    default_budget = 50
    budget = LLM_EVIDENCE_BUDGET_BY_SCOPE.get(scope, default_budget)
    return max(0, min(max_issues, budget))


def evidence_quality_rank(state: GraphState) -> GraphState:
    evidence_pool = state.get("evidence_pool") or state.get("evidence_items") or []
    plan = state.get("search_plan") or {}
    ranked = EvidenceQualityRanker(plan).rank(evidence_pool)
    max_issues = int(plan.get("max_issues") or 80)
    ranked_for_evidence = ranked[:max_issues]
    llm_budget = _llm_evidence_budget(plan, max_issues)
    ranked_for_llm = ranked_for_evidence[:llm_budget]
    return {
        **state,
        "evidence_pool": evidence_pool,
        "ranked_evidence_items": ranked_for_llm,
        "evidence_items": ranked_for_evidence,
        "llm_evidence_budget": llm_budget,
        "ranked_evidence_total_count": len(ranked_for_evidence),
    }
