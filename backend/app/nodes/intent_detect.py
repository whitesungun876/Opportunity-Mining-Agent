"""Intent detection node for the dynamic search path."""

from __future__ import annotations

from app.graph.state import GraphState
from app.search.intent import detect_search_intent


def intent_detect(state: GraphState) -> GraphState:
    query_scope = state.get("query_scope") or {}
    if query_scope.get("scope") == "repo_specific" and query_scope.get("repo_owner") and query_scope.get("repo_name"):
        topic = f"{query_scope['repo_owner']}/{query_scope['repo_name']}"
        return {
            **state,
            "canonical_topic": topic,
            "search_intent": {
                "intent": "repo",
                "normalized_topic": topic,
                "confidence": query_scope.get("confidence", 0.95),
                "reason": "Repo-specific scope detected.",
            },
        }

    topic = (state.get("user_query") or state.get("canonical_topic") or "").strip()
    intent = detect_search_intent(topic)
    return {
        **state,
        "canonical_topic": intent.normalized_topic or topic,
        "search_intent": intent.model_dump(),
    }
