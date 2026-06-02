"""Commercial validation schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class BuyerHypothesis(BaseModel):
    opportunity_id: str
    end_user: str
    economic_buyer: str
    buyer_persona: str
    budget_source: str
    buying_trigger: str
    confidence: float
    evidence_ids: list[str]


class WillingnessToPaySignal(BaseModel):
    opportunity_id: str
    signal_type: str
    signal_summary: str
    strength: Literal["weak", "medium", "strong"]
    reason: str
    evidence_ids: list[str]


class CompetitorAlternative(BaseModel):
    opportunity_id: str
    name: str
    type: Literal["open_source", "commercial", "internal_workaround", "manual_process", "unknown"]
    how_users_use_it: str
    limitation: str
    confidence: float
    source: str | None = None


class OutreachTarget(BaseModel):
    opportunity_id: str
    github_user: str | None
    source_url: str
    source_repo: str
    pain_type: str
    why_contact: str
    outreach_angle: str


class ValidationPlan(BaseModel):
    opportunity_id: str
    goal: str
    seven_day_plan: list[str]
    success_criteria: list[str]
    failure_criteria: list[str]
    recommended_next_step: Literal["build", "validate", "watch", "reject"]


class StartupMemo(BaseModel):
    opportunity_id: str
    title: str
    target_buyer: str
    end_user: str
    pain_summary: str
    evidence_summary: str
    commercial_gap: str
    current_alternatives: list[str]
    willingness_to_pay_hypothesis: str
    mvp: list[str]
    pricing_hypothesis: str
    outreach_targets: list[str]
    validation_plan: list[str]
    risks: list[str]
    final_decision: Literal["build", "validate", "watch", "reject"]
