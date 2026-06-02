"""SearchIntent schema and rule detector tests."""

from app.search.intent import detect_intent_rules
from app.search.schemas import SearchIntent


def test_search_intent_schema_for_repo():
    intent = detect_intent_rules("langfuse/langfuse")

    assert isinstance(intent, SearchIntent)
    assert intent.intent == "repo"
    assert intent.normalized_topic == "langfuse/langfuse"
    assert intent.confidence > 0.9


def test_search_intent_schema_for_problem():
    intent = detect_intent_rules("deployment pain with auth issue")

    assert intent.intent == "problem"
    assert "Problem" in intent.reason or "problem" in intent.reason.lower()
