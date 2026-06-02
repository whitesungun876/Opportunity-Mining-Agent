"""Query scope detection node."""

from __future__ import annotations

from app.graph.state import GraphState
from app.search.scope import detect_query_scope


def query_scope_detect(state: GraphState) -> GraphState:
    query = (state.get("user_query") or state.get("canonical_topic") or "").strip()
    scope = detect_query_scope(query)
    return {
        **state,
        "canonical_topic": scope.normalized_query or query,
        "query_scope": scope.model_dump(),
        "refinement_required": scope.refinement_required,
        "refinement_question": scope.refinement_question,
        "suggested_queries": scope.suggested_queries,
    }
