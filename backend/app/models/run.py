"""Run API models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Run(BaseModel):
    run_id: str
    user_query: str
    canonical_topic: str | None = None


class RunCreateRequest(BaseModel):
    topic: str = Field(min_length=1)
    dynamic_search: bool = True
    preflight_id: str | None = None
    run_mode: Literal["quick", "standard", "deep"] = "standard"
    invite_code: str | None = None


class RunCreateResponse(BaseModel):
    run_id: str
    status: str


class RunPreflightRequest(BaseModel):
    topic: str = Field(min_length=1)
    dynamic_search: bool = True
    invite_code: str | None = None


class RunPreflightResponse(BaseModel):
    preflight_id: str | None = None
    topic: str
    normalized_topic: str
    query_scope: str
    opportunity_fit: str
    should_run: bool
    reason: str
    estimated_cost: str
    estimated_runtime: str
    evidence_count: int
    strong_evidence_count: int
    repo_count: int
    suggested_queries: list[str] = Field(default_factory=list)
    search_plan: dict[str, Any] = Field(default_factory=dict)
    signal_diagnostics: dict[str, Any] = Field(default_factory=dict)


class RunSummary(BaseModel):
    run_id: str
    topic: str
    canonical_topic: str | None = None
    status: str
    created_at: str
    updated_at: str
    dynamic_search: bool
    evidence_items_count: int
    opportunity_cards_count: int
    validated_cards_count: int
    rejected_cards_count: int
    errors_count: int
    search_plan: dict[str, Any] = Field(default_factory=dict)


class RunListItem(BaseModel):
    run_id: str
    topic: str
    canonical_topic: str | None = None
    status: str
    created_at: str
    updated_at: str
    dynamic_search: bool
    validated_cards_count: int
    errors_count: int
