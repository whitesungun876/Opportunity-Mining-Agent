"""Low-signal diagnostics for recovery and user-facing explanations."""

from __future__ import annotations

from typing import Any

from app.graph.state import GraphState
from app.search.schemas import SignalDiagnostics


RECOVERY_ACTIONS: dict[str, list[str]] = {
    "repo_search": ["broaden_topic", "add_synonyms", "try_related_terms"],
    "issue_collect": ["increase_issue_limit", "include_discussions", "use_global_issue_search"],
    "evidence_rank": ["add_production_signals", "add_enterprise_signals", "try_related_terms"],
    "issue_classify": ["broaden_high_value_definition", "include_workflow_friction", "include_repeated_feature_requests"],
    "pain_extract": ["include_workflow_friction", "ask_for_more_specific_query", "expand_search"],
    "cluster": ["expand_search", "broaden_topic", "include_repeated_feature_requests"],
    "opportunity_generate": ["show_weak_signals", "expand_search", "ask_for_more_specific_query"],
    "evidence_validate": ["expand_search", "show_weak_signals", "ask_for_more_specific_query"],
    "unknown": [],
}

TYPE_RECOVERY_ACTIONS: dict[str, list[str]] = {
    "evidence_scattered": ["narrow_to_cluster", "choose_specific_workflow", "merge_similar_clusters", "try_focused_query"],
    "evidence_sparse": ["broaden_topic", "add_synonyms", "try_related_terms"],
    "classifier_too_strict": ["broaden_high_value_definition", "include_workflow_friction", "include_repeated_feature_requests"],
    "validator_too_strict": ["expand_search", "show_weak_signals", "ask_for_more_specific_query"],
    "unknown": [],
}


REASONS: dict[str, str] = {
    "repo_search": "No selected repositories were found, so the system could not collect enough GitHub evidence.",
    "issue_collect": "Repositories were found, but too few issues or discussions were collected for reliable opportunity validation.",
    "evidence_rank": "Raw GitHub activity was collected, but too few items survived evidence ranking.",
    "issue_classify": "The evidence pool exists, but too few issues look like production workflow, integration, enterprise, or repeated-feature pain.",
    "pain_extract": "High-value issues were found, but too few structured pain points could be extracted.",
    "cluster": "Pain points were found, but they did not repeat strongly enough to form a reliable cluster.",
    "opportunity_generate": "Pain clusters exist, but no evidence-grounded opportunity hypotheses were generated.",
    "evidence_validate": "Opportunity hypotheses were generated, but strict evidence validation rejected them.",
    "unknown": "The run did not expose a clear low-signal bottleneck.",
}

SCATTERED_REASON = "Evidence was found, but signals were spread across too many pain clusters to validate a focused opportunity."


def _repo_coverage(state: GraphState) -> int:
    repos = {
        str(item.get("repo") or f"{item.get('repo_owner')}/{item.get('repo_name')}")
        for item in state.get("evidence_items") or []
        if item.get("repo") or item.get("repo_owner") or item.get("repo_name")
    }
    repos.update(
        str(repo.get("full_name") or repo.get("name_with_owner") or repo.get("repo_id") or "")
        for repo in state.get("selected_repos") or []
        if isinstance(repo, dict)
    )
    return len([repo for repo in repos if repo and repo != "/"])


def _counts(state: GraphState) -> dict[str, int]:
    kept_clusters = len(state.get("pain_clusters") or [])
    filtered_clusters = len(state.get("rejected_pain_clusters") or [])
    return {
        "raw_issues_count": len(state.get("raw_issues") or []),
        "evidence_items_count": len(state.get("evidence_items") or []),
        "ranked_evidence_count": len(state.get("ranked_evidence_items") or []),
        "selected_repos_count": len(state.get("selected_repos") or []),
        "repo_coverage_count": _repo_coverage(state),
        "classified_issues_count": len(state.get("classified_issues") or []),
        "high_value_issues_count": len(state.get("high_value_issues") or []),
        "low_value_issues_count": len(state.get("low_value_issues") or []),
        "pain_points_count": len(state.get("pain_points") or []),
        "pain_clusters_count": kept_clusters + filtered_clusters,
        "filtered_pain_clusters_count": filtered_clusters,
        "commercial_gaps_count": len(state.get("commercial_gaps") or []),
        "opportunity_cards_count": len(state.get("opportunity_cards") or []),
        "validated_cards_count": len(state.get("validated_cards") or []),
        "rejected_cards_count": len(state.get("rejected_cards") or []),
    }


def diagnose_signal(state: GraphState | dict[str, Any]) -> SignalDiagnostics:
    data = _counts(state)  # type: ignore[arg-type]
    stage = "unknown"
    signal_type = "unknown"

    if data["evidence_items_count"] >= 30 and data["pain_clusters_count"] >= 10 and data["validated_cards_count"] == 0:
        stage = "cluster"
        signal_type = "evidence_scattered"
    elif data["selected_repos_count"] == 0:
        stage = "repo_search"
        signal_type = "evidence_sparse"
    elif data["raw_issues_count"] < 10:
        stage = "issue_collect"
        signal_type = "evidence_sparse"
    elif data["evidence_items_count"] < 10 or data["ranked_evidence_count"] < 5:
        stage = "evidence_rank"
        signal_type = "evidence_sparse"
    elif data["high_value_issues_count"] < 3:
        stage = "issue_classify"
        signal_type = "classifier_too_strict"
    elif data["pain_points_count"] < 3:
        stage = "pain_extract"
        signal_type = "classifier_too_strict"
    elif data["pain_clusters_count"] == 0:
        stage = "cluster"
        signal_type = "evidence_sparse"
    elif data["opportunity_cards_count"] == 0:
        stage = "opportunity_generate"
        signal_type = "evidence_scattered" if data["evidence_items_count"] >= 30 else "unknown"
    elif data["validated_cards_count"] == 0:
        stage = "evidence_validate"
        signal_type = "validator_too_strict"

    reason = SCATTERED_REASON if signal_type == "evidence_scattered" and stage == "cluster" else REASONS[stage]
    actions = TYPE_RECOVERY_ACTIONS["evidence_scattered"] if signal_type == "evidence_scattered" else RECOVERY_ACTIONS[stage]

    return SignalDiagnostics(
        **data,
        low_signal_type=signal_type,  # type: ignore[arg-type]
        low_signal_stage=stage,  # type: ignore[arg-type]
        low_signal_reason=reason,
        suggested_recovery_actions=actions,
    )


def signal_diagnostics(state: GraphState) -> GraphState:
    diagnostics = diagnose_signal(state).model_dump()
    return {**state, "signal_diagnostics": diagnostics}
