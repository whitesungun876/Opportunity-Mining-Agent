"""Pydantic models: PainPoint, OpportunityCluster, ScoreCard, RunSummary."""

from __future__ import annotations

from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

# Validator output
Verdict = Literal["pass", "needs_retry", "fail"]


class EvidenceCheck(BaseModel):
    """Per-cluster evidence quality metrics."""

    evidence_coverage: float = Field(..., ge=0, le=1, description="Share of pain points that have evidence")
    evidence_grounded: float = Field(..., ge=0, le=1, description="Whether evidence can be found in source text (coarse check)")
    duplicate_evidence_ratio: float = Field(..., ge=0, le=1, description="Evidence duplication ratio (higher suggests copy-paste)")
    missing_evidence_reasons: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Per-opportunity validation result from Validator node."""

    theme: str = Field(..., description="Opportunity theme being validated")
    verdict: Verdict = Field(..., description="pass / needs_retry / fail")
    confidence: float = Field(..., ge=0, le=1, description="Validation confidence / trust level")
    reasons: list[str] = Field(default_factory=list)
    followup_questions: list[str] = Field(default_factory=list)
    evidence_check: EvidenceCheck = Field(..., description="Evidence quality metrics")


class PainPoint(BaseModel):
    """
    A single structured pain point (from one or more user comments).
    """

    complaint: str = Field(..., description="What the user is unhappy or complaining about")
    cause: str = Field(..., description="Why this dissatisfaction occurs")
    persona: str = Field(..., description="Who is complaining (e.g. student, developer, parent)")
    context: str = Field(..., description="Usage context (when / in what situation)")
    action_intent: str = Field(..., description="Action intent (e.g. want to switch, seek alternative, willing to pay)")
    evidence: list[str] = Field(..., description="Evidence snippets from original comments")


class OpportunityCluster(BaseModel):
    """
    A clustered opportunity theme.
    """

    theme: str = Field(..., description="Core theme of this opportunity")
    pain_points: list[PainPoint] = Field(..., description="Pain points under this theme")
    sample_size: int = Field(..., description="Number of comments covered by this theme")
    confidence: float = Field(..., ge=0, le=1, description="Theme confidence / stability")


class ScoreCard(BaseModel):
    """
    Business score for one opportunity.
    """

    pain_severity: float = Field(..., ge=0, le=5)
    market_size: float = Field(..., ge=0, le=5)
    willingness_to_pay: float = Field(..., ge=0, le=5)
    competition_level: float = Field(..., ge=0, le=5)
    feasibility: float = Field(..., ge=0, le=5)

    total_score: float | None = None

    @model_validator(mode="after")
    def compute_total(self) -> "ScoreCard":
        self.total_score = (
            self.pain_severity
            + self.market_size
            + self.willingness_to_pay
            + self.competition_level
            + self.feasibility
        )
        return self


class RunSummary(BaseModel):
    """
    Output summary of one full run.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    topic: str = Field(..., description="Run topic / query")
    clusters: list[OpportunityCluster] = Field(..., description="Opportunity clusters")
    scorecards: list[ScoreCard] = Field(..., description="Score cards per cluster")
    overall_quality: float = Field(..., description="Overall run quality score")


class RunStatus(str, Enum):
    """Status of a single run."""

    PENDING = "pending"
    COLLECTING = "collecting"
    CLEANING = "cleaning"
    EXTRACTING = "extracting"
    CLUSTERING = "clustering"
    VALIDATING = "validating"
    SCORING = "scoring"
    REPORTING = "reporting"
    DONE = "done"
    FAILED = "failed"
