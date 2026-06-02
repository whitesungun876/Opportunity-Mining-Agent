"""Intent detection for dynamic GitHub search planning."""

from __future__ import annotations

import re
from typing import Any

from app.config import get_settings
from app.search.schemas import SearchIntent, SearchIntentName
from app.services.llm_client import LLMClient, parse_json_object


INTENT_SCHEMA = {
    "intent": "topic | repo | org | technology | problem | market | unknown",
    "normalized_topic": "str",
    "confidence": "float 0..1",
    "reason": "str",
}


def _coerce_intent(value: Any) -> SearchIntentName:
    text = str(value or "topic").strip().lower()
    if text in {"topic", "repo", "org", "technology", "problem", "market", "unknown"}:
        return text  # type: ignore[return-value]
    return "topic"


def _coerce_confidence(value: Any, default: float = 0.65) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = default
    return max(0.0, min(1.0, confidence))


def detect_intent_rules(user_query: str) -> SearchIntent:
    """Infer search intent without network or LLM calls."""
    query = user_query.strip()
    lowered = query.lower()
    if not query:
        return SearchIntent(intent="unknown", normalized_topic="", confidence=0.0, reason="Empty query.")
    if re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", query):
        return SearchIntent(intent="repo", normalized_topic=query, confidence=0.95, reason="owner/repo pattern.")
    if lowered.startswith(("org:", "owner:", "github org ")) or lowered.startswith("@"):
        normalized = query.removeprefix("@")
        return SearchIntent(intent="org", normalized_topic=normalized, confidence=0.85, reason="Organization search pattern.")
    if any(term in lowered for term in ["deployment pain", "auth issue", "eval problem", "problem", "blocker", "can't", "cannot", "pain"]):
        return SearchIntent(intent="problem", normalized_topic=query, confidence=0.78, reason="Problem or blocker wording.")
    if any(term in lowered for term in ["market", "startup", "saas", "opportunity", "commercial"]):
        return SearchIntent(intent="market", normalized_topic=query, confidence=0.72, reason="Market or commercial wording.")
    if any(term in lowered for term in ["framework", "tools", "tool", "platform", "database", "protocol", "sdk", "api"]):
        return SearchIntent(intent="technology", normalized_topic=query, confidence=0.78, reason="Technology category wording.")
    return SearchIntent(intent="topic", normalized_topic=query, confidence=0.65, reason="Default topic search.")


def parse_search_intent_response(response: str | dict[str, Any], user_query: str) -> SearchIntent:
    data = parse_json_object(response)
    return SearchIntent(
        intent=_coerce_intent(data.get("intent")),
        normalized_topic=str(data.get("normalized_topic") or user_query).strip(),
        confidence=_coerce_confidence(data.get("confidence")),
        reason=str(data.get("reason") or "LLM intent response.").strip(),
    )


def detect_search_intent(user_query: str) -> SearchIntent:
    """Detect intent; LLM mode is optional and never calls GitHub."""
    settings = get_settings()
    fallback = detect_intent_rules(user_query)
    if settings.mock_mode or not settings.llm_api_key:
        return fallback

    prompt = (
        "Classify the user's GitHub opportunity-mining search intent. "
        "Return JSON only. Do not search the web or GitHub.\n\n"
        f"User query: {user_query}\n\n"
        f"Schema: {INTENT_SCHEMA}"
    )
    try:
        with LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            mock_mode=False,
            cache_enabled=settings.llm_cache_enabled,
        ) as client:
            response = client.structured(prompt, INTENT_SCHEMA, system_prompt="You classify search intent. Return JSON only.")
        parsed = parse_search_intent_response(response, user_query)
        if parsed.confidence < 0.4:
            return fallback
        return parsed
    except Exception:
        return fallback


def detect_intent(user_query: str) -> SearchIntentName:
    """Backwards-compatible helper returning only the intent string."""
    return detect_search_intent(user_query).intent
