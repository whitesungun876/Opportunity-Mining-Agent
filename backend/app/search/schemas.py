"""Search planner schemas for product-path dynamic search."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


SearchIntentName = Literal[
    "topic",
    "repo",
    "org",
    "technology",
    "problem",
    "market",
    "unknown",
]


QueryScopeName = Literal[
    "broad",
    "focused",
    "repo_specific",
    "ambiguous",
]

LowSignalStageName = Literal[
    "repo_search",
    "issue_collect",
    "evidence_rank",
    "issue_classify",
    "pain_extract",
    "cluster",
    "opportunity_generate",
    "evidence_validate",
    "unknown",
]

LowSignalTypeName = Literal[
    "evidence_sparse",
    "evidence_scattered",
    "classifier_too_strict",
    "validator_too_strict",
    "unknown",
]


class SearchIntent(BaseModel):
    intent: SearchIntentName
    normalized_topic: str
    confidence: float
    reason: str


class QueryScopeDetection(BaseModel):
    scope: QueryScopeName
    normalized_query: str
    confidence: float
    reason: str

    repo_owner: str | None = None
    repo_name: str | None = None

    refinement_required: bool = False
    refinement_question: str | None = None
    suggested_queries: list[str] = Field(default_factory=list)

    breadth_score: float = 0.0
    specificity_score: float = 0.0


class SearchPlan(BaseModel):
    topic: str
    intent: SearchIntentName
    query_scope: QueryScopeName = "broad"

    seed_terms: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    repo_hints: list[str] = Field(default_factory=list)

    repo_search_queries: list[str] = Field(default_factory=list)
    global_issue_queries: list[str] = Field(default_factory=list)
    repo_issue_queries: list[str] = Field(default_factory=list)
    discussion_queries: list[str] = Field(default_factory=list)

    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)

    max_repos: int = 8
    max_issues: int = 80
    expansion_budget: int = 2

    refinement_required: bool = False
    refinement_question: str | None = None
    suggested_queries: list[str] = Field(default_factory=list)

    diversity_target: int = 3
    precision_target: float = 0.7

    # Eval profile injection is intentionally explicit so artifacts can show
    # when benchmark queries replaced dynamic issue queries.
    source: Literal["dynamic", "eval_profile"] = "dynamic"


class SignalDiagnostics(BaseModel):
    raw_issues_count: int = 0
    evidence_items_count: int = 0
    ranked_evidence_count: int = 0
    selected_repos_count: int = 0
    repo_coverage_count: int = 0
    classified_issues_count: int = 0
    high_value_issues_count: int = 0
    low_value_issues_count: int = 0
    pain_points_count: int = 0
    pain_clusters_count: int = 0
    filtered_pain_clusters_count: int = 0
    commercial_gaps_count: int = 0
    opportunity_cards_count: int = 0
    validated_cards_count: int = 0
    rejected_cards_count: int = 0
    low_signal_type: LowSignalTypeName = "unknown"
    low_signal_stage: LowSignalStageName = "unknown"
    low_signal_reason: str = ""
    suggested_recovery_actions: list[str] = Field(default_factory=list)
