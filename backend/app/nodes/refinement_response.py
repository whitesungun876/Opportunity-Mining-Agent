"""Early response for ambiguous user queries."""

from __future__ import annotations

from app.graph.state import GraphState


def refinement_response(state: GraphState) -> GraphState:
    question = state.get("refinement_question") or "Please refine the query before running opportunity mining."
    suggestions = state.get("suggested_queries") or []
    lines = [
        "# Query Refinement Needed",
        "",
        str(question),
        "",
        "## Suggested queries",
    ]
    for suggestion in suggestions:
        lines.append(f"- {suggestion}")
    return {
        **state,
        "opportunity_cards": [],
        "validated_cards": [],
        "rejected_cards": [],
        "final_decisions": [],
        "agent_reviews": [],
        "report_markdown": "\n".join(lines),
        "status": "needs_refinement",
    }
