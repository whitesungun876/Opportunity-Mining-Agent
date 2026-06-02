"""Base skill contracts."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel


class SkillSpec(BaseModel):
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    cost_level: Literal["low", "medium", "high"]
    requires_network: bool
    max_concurrency: int = 3
    timeout_seconds: int = 30
    retry_limit: int = 2
