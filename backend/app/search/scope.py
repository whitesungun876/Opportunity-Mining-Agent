"""Query scope detection for Dynamic Search Planner.

Scope controls how wide the product search should be. It is intentionally
topic-agnostic: benchmark profiles remain in app/eval/topic_profiles.yaml.
"""

from __future__ import annotations

import re
from typing import Any

from app.config import get_settings
from app.search.schemas import QueryScopeDetection, QueryScopeName
from app.search.templates import (
    ENTERPRISE_SIGNALS,
    INTEGRATION_SIGNALS,
    OBSERVABILITY_SIGNALS,
    PRODUCTION_SIGNALS,
)
from app.services.llm_client import LLMClient, parse_json_object


REPO_URL_PATTERN = re.compile(
    r"(?:https?://)?github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)(?:/.*)?$",
    re.IGNORECASE,
)
REPO_NAME_PATTERN = re.compile(r"^(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)$")

PROBLEM_SIGNALS = {
    "auth",
    "authentication",
    "debug",
    "debugging",
    "deploy",
    "deployment",
    "eval",
    "evaluation",
    "latency",
    "observability",
    "permission",
    "production",
    "regression",
    "security",
    "trace",
    "tracing",
    "workflow",
}
TECH_CATEGORY_SIGNALS = {
    "agent",
    "framework",
    "mcp",
    "rag",
    "tool",
    "tools",
    "database",
    "platform",
    "protocol",
    "sdk",
}

SCOPE_SCHEMA = {
    "scope": "broad | focused | repo_specific | ambiguous",
    "normalized_query": "str",
    "confidence": "float 0..1",
    "reason": "str",
    "repo_owner": "str | null",
    "repo_name": "str | null",
    "refinement_required": "bool",
    "refinement_question": "str | null",
    "suggested_queries": "list[str]",
    "breadth_score": "float 0..1",
    "specificity_score": "float 0..1",
}


def _tokens(query: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9_.+-]*", query.lower())


def _repo_match(query: str) -> tuple[str, str] | None:
    stripped = query.strip().removesuffix("/")
    match = REPO_URL_PATTERN.match(stripped) or REPO_NAME_PATTERN.match(stripped)
    if not match:
        return None
    repo = match.group("repo").removesuffix(".git")
    return match.group("owner"), repo


def _suggestions(query: str) -> list[str]:
    base = query.strip() or "AI developer tools"
    if base.lower() in {"agent", "agents"}:
        base = "AI agent framework"
    if base.lower() in {"rag"}:
        base = "RAG evaluation"
    if base.lower() in {"mcp"}:
        base = "MCP tools"
    return [
        f"{base} production deployment",
        f"{base} observability for debugging",
        f"{base} enterprise auth and permissions",
    ]


def _score_specificity(tokens: list[str], query: str) -> float:
    lowered = query.lower()
    problem_hits = len({token for token in tokens if token in PROBLEM_SIGNALS})
    signal_hits = sum(1 for signal in PROBLEM_SIGNALS if signal in lowered)
    return min(1.0, (len(tokens) / 8.0) * 0.45 + problem_hits * 0.18 + signal_hits * 0.08)


def _scope_from_value(value: Any) -> QueryScopeName:
    text = str(value or "broad").strip().lower()
    if text in {"broad", "focused", "repo_specific", "ambiguous"}:
        return text  # type: ignore[return-value]
    return "broad"


def detect_query_scope_rules(user_query: str) -> QueryScopeDetection:
    """Classify query breadth without network or LLM calls."""
    query = user_query.strip()
    tokens = _tokens(query)
    lowered = query.lower()
    if not query:
        return QueryScopeDetection(
            scope="ambiguous",
            normalized_query="",
            confidence=0.95,
            reason="Empty query.",
            refinement_required=True,
            refinement_question="What GitHub technology, repo, or production problem should be analyzed?",
            suggested_queries=_suggestions("AI developer tools"),
            breadth_score=1.0,
            specificity_score=0.0,
        )

    repo = _repo_match(query)
    if repo:
        owner, name = repo
        return QueryScopeDetection(
            scope="repo_specific",
            normalized_query=f"{owner}/{name}",
            confidence=0.98,
            reason="Query matches a GitHub owner/repo reference.",
            repo_owner=owner,
            repo_name=name,
            breadth_score=0.1,
            specificity_score=1.0,
        )

    specificity = _score_specificity(tokens, query)
    breadth = max(0.0, 1.0 - specificity)
    if len(tokens) <= 1:
        return QueryScopeDetection(
            scope="ambiguous",
            normalized_query=query,
            confidence=0.88,
            reason="Single-word query is too broad to produce useful opportunity cards.",
            refinement_required=True,
            refinement_question=f"What specific {query} direction should be analyzed?",
            suggested_queries=_suggestions(query),
            breadth_score=0.95,
            specificity_score=specificity,
        )

    has_problem_signal = any(signal in lowered for signal in PROBLEM_SIGNALS)
    if has_problem_signal and (len(tokens) >= 4 or specificity >= 0.55):
        return QueryScopeDetection(
            scope="focused",
            normalized_query=query,
            confidence=0.82,
            reason="Query combines a domain with production/problem workflow signals.",
            breadth_score=breadth,
            specificity_score=max(specificity, 0.65),
        )

    has_category_signal = any(token in TECH_CATEGORY_SIGNALS for token in tokens)
    if has_category_signal or len(tokens) <= 4:
        return QueryScopeDetection(
            scope="broad",
            normalized_query=query,
            confidence=0.78,
            reason="Query describes a technology/category without a narrow production pain.",
            breadth_score=max(breadth, 0.65),
            specificity_score=specificity,
        )

    return QueryScopeDetection(
        scope="focused" if specificity >= 0.6 else "broad",
        normalized_query=query,
        confidence=0.68,
        reason="Rule-based scope inferred from query specificity.",
        breadth_score=breadth,
        specificity_score=specificity,
    )


def parse_query_scope_response(response: str | dict[str, Any], user_query: str) -> QueryScopeDetection:
    data = parse_json_object(response)
    fallback = detect_query_scope_rules(user_query)
    scope = _scope_from_value(data.get("scope"))
    return QueryScopeDetection(
        scope=scope,
        normalized_query=str(data.get("normalized_query") or fallback.normalized_query).strip(),
        confidence=max(0.0, min(1.0, float(data.get("confidence") or fallback.confidence))),
        reason=str(data.get("reason") or fallback.reason).strip(),
        repo_owner=data.get("repo_owner") or fallback.repo_owner,
        repo_name=data.get("repo_name") or fallback.repo_name,
        refinement_required=bool(data.get("refinement_required", fallback.refinement_required)),
        refinement_question=data.get("refinement_question") or fallback.refinement_question,
        suggested_queries=[str(item) for item in data.get("suggested_queries") or fallback.suggested_queries],
        breadth_score=max(0.0, min(1.0, float(data.get("breadth_score") or fallback.breadth_score))),
        specificity_score=max(0.0, min(1.0, float(data.get("specificity_score") or fallback.specificity_score))),
    )


def detect_query_scope(user_query: str) -> QueryScopeDetection:
    """Detect query scope; LLM mode is optional and never calls GitHub."""
    settings = get_settings()
    fallback = detect_query_scope_rules(user_query)
    if settings.mock_mode or not settings.llm_api_key:
        return fallback

    prompt = (
        "Classify the scope of a GitHub opportunity-mining user query. "
        "Return JSON only. Do not search the web or GitHub.\n\n"
        "Scope meanings:\n"
        "- broad: technology/category exploration.\n"
        "- focused: specific production problem or workflow validation.\n"
        "- repo_specific: a concrete GitHub owner/repo.\n"
        "- ambiguous: too short/vague; should ask for refinement.\n\n"
        f"User query: {user_query}\n\nSchema: {SCOPE_SCHEMA}"
    )
    try:
        with LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            mock_mode=False,
            cache_enabled=settings.llm_cache_enabled,
        ) as client:
            response = client.structured(prompt, SCOPE_SCHEMA, system_prompt="You classify query scope. Return JSON only.")
        parsed = parse_query_scope_response(response, user_query)
        if parsed.confidence < 0.45:
            return fallback
        return parsed
    except Exception:
        return fallback
