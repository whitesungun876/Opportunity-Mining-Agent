"""Adaptive query expansion for weak evidence pools."""

from __future__ import annotations

from typing import Any

from app.search.planner import expand_search_plan
from app.search.schemas import SearchPlan


class AdaptiveQueryExpander:
    """Expand a SearchPlan only when evidence quality is insufficient."""

    def expand(self, plan: SearchPlan, evidence_stats: dict[str, Any]) -> tuple[SearchPlan, str]:
        if plan.expansion_budget <= 0:
            return plan, "expansion_budget exhausted"
        evidence_count = int(evidence_stats.get("evidence_count") or 0)
        repo_count = int(evidence_stats.get("repo_count") or 0)
        strong_count = int(evidence_stats.get("strong_evidence_count") or 0)
        if evidence_count >= 15 and repo_count >= 3:
            return plan, "sufficient evidence count and repo coverage"
        if strong_count >= 8:
            return plan, "sufficient strong evidence"
        expanded = expand_search_plan(plan, iteration_count=int(evidence_stats.get("iteration_count") or 0) + 1)
        stage = str(evidence_stats.get("low_signal_stage") or "evidence_rank")
        return expanded, (
            f"expanded for {stage} because evidence_count={evidence_count}, "
            f"repo_count={repo_count}, strong_evidence_count={strong_count}"
        )


def expand_for_quality_gap(plan: SearchPlan, *, iteration_count: int) -> SearchPlan:
    """Backwards-compatible helper."""
    expanded, _ = AdaptiveQueryExpander().expand(
        plan,
        {
            "evidence_count": 0,
            "repo_count": 0,
            "strong_evidence_count": 0,
            "iteration_count": iteration_count,
        },
    )
    return expanded
