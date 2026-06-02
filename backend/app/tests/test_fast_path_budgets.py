"""P0 fast-path budget and gate tests."""

from app.nodes.evidence_quality_rank import evidence_quality_rank
from app.nodes.opportunity_generate import select_gap_candidates
from app.nodes.topic_cluster import _apply_cluster_quality_gate
from app.graph.main_graph import _after_card_validation
from app.search.expansion import AdaptiveQueryExpander
from app.search.intent import detect_intent_rules
from app.search.planner import generate_search_plan
from app.search.schemas import SearchPlan
from app.search.scope import detect_query_scope_rules


def _evidence_item(idx: int) -> dict:
    return {
        "evidence_id": f"ev_{idx}",
        "repo_owner": "owner",
        "repo_name": f"repo-{idx % 5}",
        "title": "production deployment observability debugging evaluation workflow",
        "body": "teams need production integration and tracing at scale",
        "comment_count": idx % 12,
        "reaction_count": idx % 4,
        "state": "OPEN",
    }


def test_scope_budgets_are_fast_path_sized():
    repo_scope = detect_query_scope_rules("langfuse/langfuse")
    repo_plan = generate_search_plan(repo_scope.normalized_query, detect_intent_rules(repo_scope.normalized_query), repo_scope)
    assert repo_plan.max_issues == 40

    focused_scope = detect_query_scope_rules("RAG regression testing before deployment")
    focused_plan = generate_search_plan(
        focused_scope.normalized_query,
        detect_intent_rules(focused_scope.normalized_query),
        focused_scope,
    )
    assert focused_plan.max_issues == 50

    broad_scope = detect_query_scope_rules("AI agent framework")
    broad_plan = generate_search_plan(broad_scope.normalized_query, detect_intent_rules(broad_scope.normalized_query), broad_scope)
    assert broad_plan.max_issues == 80


def test_evidence_quality_rank_caps_llm_candidates_but_keeps_audit_evidence():
    evidence = [_evidence_item(idx) for idx in range(70)]
    state = {
        "evidence_pool": evidence,
        "search_plan": {
            "query_scope": "repo_specific",
            "max_issues": 40,
            "positive_signals": ["production", "deployment", "observability", "debugging"],
            "negative_signals": ["install failed"],
        },
    }

    ranked_state = evidence_quality_rank(state)

    assert len(ranked_state["evidence_items"]) == 40
    assert len(ranked_state["ranked_evidence_items"]) == 30
    assert ranked_state["llm_evidence_budget"] == 30


def test_cluster_quality_gate_rejects_weak_clusters():
    clusters = [
        {
            "cluster_id": "strong",
            "evidence_ids": ["ev_1", "ev_2", "ev_3"],
            "evidence_count": 3,
            "severity_score": 0.7,
            "repetition_score": 0.6,
        },
        {
            "cluster_id": "weak",
            "evidence_ids": ["ev_4"],
            "evidence_count": 1,
            "severity_score": 0.9,
            "repetition_score": 0.2,
        },
    ]

    kept, rejected = _apply_cluster_quality_gate(clusters)

    assert [cluster["cluster_id"] for cluster in kept] == ["strong"]
    assert rejected[0]["cluster_id"] == "weak"
    assert rejected[0]["rejection_reason"]


def test_cluster_quality_gate_enriches_rejected_clusters_with_matched_signals():
    clusters = [
        {
            "cluster_id": "weak",
            "evidence_ids": ["ev_1"],
            "evidence_count": 1,
            "severity_score": 0.8,
            "repetition_score": 0.2,
            "pain_type": "permission_gap",
        }
    ]
    evidence_items = [
        {
            "evidence_id": "ev_1",
            "matched_signals": ["rbac", "audit", "permission"],
        }
    ]

    _, rejected = _apply_cluster_quality_gate(clusters, evidence_items)

    assert rejected[0]["matched_signals"] == ["rbac", "audit", "permission"]


def test_select_gap_candidates_prefers_evidence_and_avoids_weak_consulting():
    gaps = [
        {
            "gap_id": "weak_consulting",
            "evidence_ids": ["ev_1", "ev_2", "ev_3", "ev_4"],
            "confidence": 0.6,
            "migration_cost": "high",
            "consulting_vs_saas": "consulting_like",
            "best_product_form": "Consulting",
        },
        {
            "gap_id": "strong_saas",
            "evidence_ids": ["ev_1", "ev_2", "ev_3"],
            "confidence": 0.8,
            "migration_cost": "medium",
            "consulting_vs_saas": "saas_possible",
            "best_product_form": "Hosted SaaS",
        },
    ]

    selected = select_gap_candidates({"search_plan": {"query_scope": "focused"}}, gaps)

    assert [gap["gap_id"] for gap in selected] == ["strong_saas"]


def test_no_validated_cards_short_circuits_advanced_intelligence():
    assert _after_card_validation({"validated_cards": []}) == "report_write"
    assert _after_card_validation({"validated_cards": [{"opportunity_id": "opp_1"}]}) == "debate"
    assert _after_card_validation({"validated_cards": [{"opportunity_id": "opp_1"}], "run_mode": "quick"}) == "report_write"
    assert _after_card_validation({"validated_cards": [{"opportunity_id": "opp_1"}], "run_mode": "deep"}) == "evidence_graph_build"


def test_adaptive_query_expand_on_low_signal():
    plan = SearchPlan(
        topic="MCP auth and permissions",
        intent="problem",
        query_scope="focused",
        seed_terms=["MCP auth and permissions"],
        synonyms=["MCP authentication", "MCP authorization"],
        global_issue_queries=['"MCP auth and permissions" production deployment type:issue'],
        expansion_budget=2,
    )

    expanded, reason = AdaptiveQueryExpander().expand(
        plan,
        {
            "evidence_count": 2,
            "repo_count": 1,
            "strong_evidence_count": 0,
            "low_signal_stage": "evidence_rank",
        },
    )

    assert expanded.expansion_budget == 1
    assert len(expanded.global_issue_queries) > len(plan.global_issue_queries)
    assert "expanded for evidence_rank" in reason
