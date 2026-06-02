"""Agent review model."""

from __future__ import annotations

from pydantic import BaseModel


class AgentReview(BaseModel):
    agent: str
    score: int
    key_argument: str
    main_risk: str
    recommendation: str
