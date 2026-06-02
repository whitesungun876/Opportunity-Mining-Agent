"""ContextPacket builders for graph nodes."""

from __future__ import annotations

from app.context.budget import budget_for
from app.context.packet import ContextPacket


def build_context_packet(
    *,
    node_name: str,
    goal: str,
    input_items: list[dict],
    evidence_ids: list[str] | None = None,
    memory_snippets: list[dict] | None = None,
    output_schema: dict | None = None,
    prompt_version: str = "mock:v1",
) -> ContextPacket:
    """Build a deterministic ContextPacket with node-level budget."""
    return ContextPacket(
        node_name=node_name,
        goal=goal,
        input_items=input_items,
        evidence_ids=evidence_ids or [],
        memory_snippets=memory_snippets or [],
        token_budget=budget_for(node_name),
        output_schema=output_schema or {},
        prompt_version=prompt_version,
    )
