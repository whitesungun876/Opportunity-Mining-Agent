"""Graph state contract."""

from typing import TypedDict, Any


class GraphState(TypedDict, total=False):
    run_id: str
    user_query: str
    canonical_topic: str
    benchmark_profile: dict[str, Any]
    benchmark_profile_id: str
    benchmark_queries: list[str]
    benchmark_quality_keywords: list[str]
    benchmark_per_query: int
    benchmark_max_issues: int
    skip_debate: bool
    preflight_id: str
    warm_start_evidence: bool
    run_mode: str
    node_latency_summary: list[dict[str, Any]]
    search_intent: dict[str, Any]
    search_plan: dict[str, Any]
    evidence_pool: list[dict]
    ranked_evidence_items: list[dict]
    ranked_evidence_total_count: int
    llm_evidence_budget: int
    query_expansions: list[dict]
    query_scope: dict[str, Any]
    refinement_required: bool
    refinement_question: str
    suggested_queries: list[str]

    github_queries: list[str]
    repo_search_queries: list[str]
    global_issue_queries: list[str]
    repo_issue_queries: list[str]
    discussion_queries: list[str]
    searched_repos: list[dict]
    selected_repos: list[dict]

    raw_issues: list[dict]
    classified_issues: list[dict]
    high_value_issues: list[dict]
    low_value_issues: list[dict]
    evidence_items: list[dict]

    pain_points: list[dict]
    pain_topics: list[dict]
    pain_clusters: list[dict]
    rejected_pain_clusters: list[dict]
    pain_extract_budget: int

    commercial_gaps: list[dict]
    commercial_gap_candidate_clusters: list[dict]
    commercial_gap_cluster_budget: int
    opportunity_cards: list[dict]
    opportunity_gap_candidates: list[dict]
    opportunity_gap_budget: int
    validated_cards: list[dict]
    rejected_cards: list[dict]
    signal_diagnostics: dict[str, Any]

    agent_reviews: list[dict]
    final_decisions: list[dict]

    report_markdown: str

    errors: list[str]
    iteration_count: int
    evidence_strength: float
    repetition_score: float
    commercial_gap_score: float
    feasibility_score: float
    quality_score: float
    opportunity_graph: dict[str, Any]
    graph_nodes: list[dict]
    graph_edges: list[dict]
    repo_capabilities: list[dict]
    research_evidence: list[dict]
    fusion_candidates: list[dict]
    validated_fusion_candidates: list[dict]
    rejected_fusion_candidates: list[dict]

    buyer_hypotheses: list[dict]
    wtp_signals: list[dict]
    competitor_alternatives: list[dict]
    outreach_targets: list[dict]
    validation_plans: list[dict]
    startup_memos: list[dict]

    # Internal runtime hooks. These are removed before persisted state is saved.
    _trace_logger: Any
    _langfuse_observer: Any
    _progress_callback: Any
