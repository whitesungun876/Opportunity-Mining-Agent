"""Opportunity models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OpportunityCard(BaseModel):
    opportunity_id: str
    title: str
    target_user: str | None = None
    source_repos: list[str] = Field(default_factory=list)
    pain_summary: str | None = None
    commercial_gap: str | None = None
    migration_cost: str
    product_form: str | None = None
    best_product_form: str | None = None
    mvp_features: list[str] = Field(default_factory=list)
    pricing_hypothesis: str | None = None
    first_users: list[str] = Field(default_factory=list)
    validation_actions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    score_json: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_urls: list[str] = Field(default_factory=list)
    weak_card: bool = False
    cluster_id: str | None = None
