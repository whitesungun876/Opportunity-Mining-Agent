"""Schemas for lightweight opportunity fusion graphs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


GraphNodeType = Literal[
    "PainPoint",
    "Repo",
    "Evidence",
    "Capability",
    "Paper",
    "Method",
    "CommercialGap",
    "Opportunity",
]

GraphEdgeType = Literal[
    "repo_has_pain",
    "repo_has_capability",
    "pain_supported_by_evidence",
    "pain_similar_to_pain",
    "capability_may_solve_pain",
    "paper_supports_method",
    "method_enables_capability",
    "pain_has_commercial_gap",
    "opportunity_combines",
    "opportunity_supported_by_evidence",
]


class GraphNode(BaseModel):
    node_id: str
    node_type: GraphNodeType
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)


class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    edge_type: GraphEdgeType
    confidence: float = 0.5
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str = ""


class OpportunityGraph(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

    def model_dump_graph(self) -> dict[str, Any]:
        return {
            "nodes": [node.model_dump() for node in self.nodes],
            "edges": [edge.model_dump() for edge in self.edges],
        }


class Capability(BaseModel):
    capability_id: str
    name: str
    description: str
    source_repo: str
    maturity_score: float
    implementation_clues: list[str] = Field(default_factory=list)
    related_methods: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ResearchEvidence(BaseModel):
    paper_id: str
    title: str
    url: str
    abstract: str
    claim_summary: str
    supports: list[str] = Field(default_factory=list)
    limitation: str
    confidence: float = 0.5


class FusionCandidate(BaseModel):
    fusion_id: str
    title: str

    user_query_anchor: str
    pain: dict[str, Any]
    capability: dict[str, Any]
    research_evidence: list[dict[str, Any]] = Field(default_factory=list)

    fusion_thesis: str
    why_combination_makes_sense: str
    product_angle: str
    target_user: str

    evidence_ids: list[str] = Field(default_factory=list)
    repo_ids: list[str] = Field(default_factory=list)
    paper_ids: list[str] = Field(default_factory=list)

    novelty_score: float = 0.0
    feasibility_score: float = 0.0
    evidence_strength: float = 0.0
    commercial_potential: float = 0.0
    overall_score: float = 0.0
    risks: list[str] = Field(default_factory=list)
