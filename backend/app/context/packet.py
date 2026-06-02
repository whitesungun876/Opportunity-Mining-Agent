"""Context packet passed into LLM/tool-facing nodes."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class ContextPacket(BaseModel):
    node_name: str
    goal: str
    input_items: list[dict]
    evidence_ids: list[str] = []
    memory_snippets: list[dict] = []
    token_budget: int
    output_schema: dict[str, Any]
    prompt_version: str
