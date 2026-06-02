"""Dynamic SearchPlan generation for product-path runs."""

from __future__ import annotations

import re
from typing import Any

from app.config import get_settings
from app.search.intent import detect_search_intent
from app.search.schemas import QueryScopeDetection, SearchIntent, SearchPlan
from app.search.templates import (
    EXPANSION_PATTERNS,
    GLOBAL_ISSUE_PATTERNS,
    NEGATIVE_SIGNAL_TERMS,
    POSITIVE_SIGNAL_TERMS,
    REPO_ISSUE_PATTERNS,
    REPO_SEARCH_PATTERNS,
)
from app.services.llm_client import LLMClient, parse_json_object


PLANNER_SEED_SCHEMA = {
    "seed_terms": "list[str]",
    "synonyms": "list[str]",
    "repo_hints": "list[str]",
}

MAX_SEED_TERMS = 4
MAX_SYNONYMS = 12
MAX_REPO_HINTS = 3
MAX_REPO_QUERIES = 8
MAX_INITIAL_GLOBAL_ISSUE_QUERIES = 12
MAX_GLOBAL_ISSUE_QUERIES = 16
MAX_DISCUSSION_QUERIES = 4

LOW_INFORMATION_TERMS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "ai",
    "tool",
    "tools",
    "framework",
    "frameworks",
    "platform",
    "platforms",
    "system",
    "systems",
    "open",
    "source",
    "open-source",
    "is",
    "are",
    "too",
    "very",
    "hard",
    "complex",
    "complicated",
    "difficult",
}

PROBLEM_STOP_WORDS = LOW_INFORMATION_TERMS | {
    "be",
    "been",
    "being",
    "can",
    "cannot",
    "cant",
    "can't",
    "do",
    "does",
    "doesnt",
    "doesn't",
    "not",
    "need",
    "needs",
    "pain",
    "problem",
    "problems",
    "issue",
    "issues",
    "struggle",
    "struggling",
}


def _dedupe(items: list[str]) -> list[str]:
    return [item for item in dict.fromkeys(str(item).strip() for item in items if str(item).strip())]


def _is_low_information_term(term: str) -> bool:
    normalized = re.sub(r"\s+", " ", term.strip().lower())
    return normalized in LOW_INFORMATION_TERMS


def _clean_terms(items: list[str], *, keep_phrases: bool = True) -> list[str]:
    cleaned: list[str] = []
    for item in items:
        term = re.sub(r"\s+", " ", str(item).strip())
        if not term:
            continue
        if _is_low_information_term(term):
            continue
        # Keep the user's full phrase, but avoid generated one-word query cores
        # that are too generic for GitHub search.
        if not keep_phrases and len(term.split()) > 1:
            continue
        cleaned.append(term)
    return _dedupe(cleaned)


def _seed_terms(topic: str) -> list[str]:
    terms = re.findall(r"[A-Za-z0-9][A-Za-z0-9_.+-]*", topic)
    seeds = [topic]
    if 1 < len(terms) <= 4:
        seeds.extend(term for term in terms if not _is_low_information_term(term))
    return _clean_terms(seeds)[:MAX_SEED_TERMS]


def _domain_translations(topic: str) -> list[str]:
    """Translate product/commercial wording into GitHub issue vocabulary."""
    lowered = topic.lower()
    translations: list[str] = []
    if any(term in lowered for term in ["security", "compliance", "permission", "rbac", "auth"]):
        translations.extend(
            [
                "sso",
                "rbac",
                "audit logs",
                "soc2",
                "permission model",
                "oauth",
                "policy scanning",
                "compliance reporting",
                "access control",
            ]
        )
    if any(term in lowered for term in ["ci", "pipeline", "security", "compliance"]):
        translations.extend(
            [
                "ci security false positives",
                "dependency scanning",
                "vulnerability triage",
                "policy checks",
            ]
        )
    if any(term in lowered for term in ["self-host", "self hosted", "deployment", "deploy"]):
        translations.extend(
            [
                "self hosted deployment",
                "helm chart",
                "docker compose",
                "kubernetes deployment",
                "upgrade migration",
            ]
        )
    if "agent" in lowered:
        translations.extend(
            [
                "LLM agent framework",
                "agent orchestration",
                "tool calling framework",
                "agent memory persistence",
                "agent tracing",
            ]
        )
    if "mcp" in lowered or "model context protocol" in lowered:
        translations.extend(
            [
                "MCP authentication",
                "MCP authorization",
                "MCP access control",
                "MCP OAuth",
                "MCP token scope",
                "MCP tool permissions",
                "model context protocol security",
            ]
        )
    return _clean_terms(translations)


def _synonyms(topic: str) -> list[str]:
    lowered = topic.lower()
    synonyms: list[str] = []
    if "rag" in lowered:
        synonyms.extend(["retrieval augmented generation", "retrieval evaluation", "groundedness"])
    if "agent" in lowered:
        synonyms.extend([
            "LLM agent framework",
            "agent orchestration",
            "tool calling framework",
            "agent memory persistence",
            "agent tracing",
        ])
    if "mcp" in lowered or "model context protocol" in lowered:
        synonyms.extend([
            "MCP authentication",
            "MCP authorization",
            "MCP access control",
            "MCP OAuth",
            "MCP token scope",
            "MCP tool permissions",
            "model context protocol security",
        ])
    if "auth" in lowered or "permission" in lowered:
        synonyms.extend(["authentication", "authorization", "access control", "OAuth", "token scope", "RBAC"])
    if "observability" in lowered or "monitoring" in lowered:
        synonyms.extend(["tracing", "monitoring", "debugging", "telemetry"])
    if "eval" in lowered or "evaluation" in lowered:
        synonyms.extend(["testing", "quality", "regression", "benchmark"])
    synonyms.extend(_domain_translations(topic))
    return _clean_terms(synonyms)[:MAX_SYNONYMS]


def _problem_search_terms(topic: str) -> list[str]:
    """Turn natural-language pain into GitHub issue-search vocabulary."""
    lowered = topic.lower().replace("self-hosted", "self hosted")
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9_.+-]*", lowered)
    meaningful = [token for token in tokens if token not in PROBLEM_STOP_WORDS and len(token) > 2]
    compact = " ".join(meaningful[:5])
    terms: list[str] = [compact] if compact else []

    if any(term in lowered for term in ["self hosted", "self-host", "deployment", "deploy"]):
        terms.extend(
            [
                "self hosted deployment",
                "deployment complexity",
                "deployment blocker",
                "helm chart kubernetes",
                "docker compose deployment",
                "upgrade migration",
            ]
        )
    if any(term in lowered for term in ["auth", "permission", "rbac", "security", "compliance"]):
        terms.extend(
            [
                "authentication authorization",
                "access control permissions",
                "rbac audit logs",
                "enterprise security",
                "oauth token scope",
            ]
        )
    if any(term in lowered for term in ["debug", "debugging", "observability", "trace", "monitor"]):
        terms.extend(
            [
                "debugging production workflow",
                "tracing observability",
                "monitoring dashboard",
                "production debugging",
            ]
        )
    if any(term in lowered for term in ["ci", "pipeline", "flaky"]):
        terms.extend(
            [
                "ci failures",
                "flaky tests",
                "pipeline debugging",
                "build failure workflow",
            ]
        )
    if any(term in lowered for term in ["rag", "evaluation", "eval", "regression"]):
        terms.extend(
            [
                "rag evaluation",
                "retrieval evaluation",
                "regression testing",
                "quality evaluation",
            ]
        )
    return _clean_terms(terms)


def _repo_hints(topic: str, intent: str, query_scope: QueryScopeDetection | None = None) -> list[str]:
    if query_scope and query_scope.scope == "repo_specific" and query_scope.repo_owner and query_scope.repo_name:
        return [f"{query_scope.repo_owner}/{query_scope.repo_name}"]
    if intent == "repo" and "/" in topic:
        return [topic.strip()]
    return []


def _coerce_seed_payload(
    value: str | dict[str, Any],
    topic: str,
    intent: SearchIntent,
    query_scope: QueryScopeDetection | None = None,
) -> dict[str, list[str]]:
    try:
        data = parse_json_object(value)
    except Exception:
        data = {}
    seed_terms = data.get("seed_terms") if isinstance(data.get("seed_terms"), list) else []
    synonyms = data.get("synonyms") if isinstance(data.get("synonyms"), list) else []
    repo_hints = data.get("repo_hints") if isinstance(data.get("repo_hints"), list) else []
    return {
        "seed_terms": _clean_terms([str(item) for item in seed_terms] + _seed_terms(topic))[:MAX_SEED_TERMS],
        "synonyms": _clean_terms([str(item) for item in synonyms] + _synonyms(topic))[:MAX_SYNONYMS],
        "repo_hints": _dedupe([str(item) for item in repo_hints] + _repo_hints(topic, intent.intent, query_scope))[:MAX_REPO_HINTS],
    }


def _llm_seed_payload(
    topic: str,
    intent: SearchIntent,
    query_scope: QueryScopeDetection | None = None,
) -> dict[str, list[str]] | None:
    settings = get_settings()
    if settings.mock_mode or not settings.llm_api_key:
        return None
    prompt = (
        "Generate compact GitHub search seed terms for opportunity mining. "
        "Only return JSON with seed_terms, synonyms, repo_hints. Do not create full GitHub queries.\n\n"
        f"Topic: {topic}\nIntent: {intent.model_dump()}\nSchema: {PLANNER_SEED_SCHEMA}"
    )
    try:
        with LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            mock_mode=False,
            cache_enabled=settings.llm_cache_enabled,
        ) as client:
            response = client.structured(prompt, PLANNER_SEED_SCHEMA, system_prompt="Return compact JSON search seeds only.")
        return _coerce_seed_payload(response, topic, intent, query_scope)
    except Exception:
        return None


def _format_patterns(patterns: list[str], terms: list[str], *, limit: int) -> list[str]:
    queries: list[str] = []
    for term in terms:
        for pattern in patterns:
            queries.append(pattern.format(term=term, topic=term))
            if len(_dedupe(queries)) >= limit:
                return _dedupe(queries)[:limit]
    return _dedupe(queries)[:limit]


def _issue_query_terms(
    topic: str,
    seed_terms: list[str],
    synonyms: list[str],
    query_scope: QueryScopeDetection | None,
) -> list[str]:
    if query_scope and query_scope.scope == "focused":
        # Focused inputs are often natural-language pain statements. GitHub
        # issue search works better with product/workflow vocabulary than with
        # quoted full sentences.
        return _clean_terms(_problem_search_terms(topic) + synonyms + [topic])[: MAX_SEED_TERMS + MAX_SYNONYMS]
    return _clean_terms([topic] + synonyms + [term for term in seed_terms if term.lower() != topic.lower()])[: MAX_SEED_TERMS + MAX_SYNONYMS]


def _apply_scope_settings(plan: SearchPlan, query_scope: QueryScopeDetection | None) -> SearchPlan:
    if not query_scope:
        return plan
    plan.query_scope = query_scope.scope
    plan.refinement_required = query_scope.refinement_required
    plan.refinement_question = query_scope.refinement_question
    plan.suggested_queries = query_scope.suggested_queries

    if query_scope.scope == "repo_specific":
        repo = f"{query_scope.repo_owner}/{query_scope.repo_name}" if query_scope.repo_owner and query_scope.repo_name else plan.topic
        plan.topic = repo
        plan.intent = "repo"
        plan.repo_hints = [repo]
        plan.repo_search_queries = [repo]
        plan.global_issue_queries = [
            f"repo:{repo} production deployment type:issue",
            f"repo:{repo} integration workflow type:issue",
            f"repo:{repo} enterprise security permission type:issue",
            f"repo:{repo} observability debugging evaluation type:issue",
            f"repo:{repo} hosted managed dashboard type:issue",
        ]
        plan.discussion_queries = [query.replace("type:issue", "type:discussion") for query in plan.global_issue_queries[:MAX_DISCUSSION_QUERIES]]
        plan.max_repos = 1
        plan.max_issues = 40
        plan.expansion_budget = 1
        plan.diversity_target = 1
        plan.precision_target = 0.85
    elif query_scope.scope == "focused":
        plan.max_repos = 6
        plan.max_issues = 50
        plan.expansion_budget = 2
        plan.diversity_target = 2
        plan.precision_target = 0.85
        plan.global_issue_queries = plan.global_issue_queries[:10]
    elif query_scope.scope == "broad":
        plan.max_repos = 10
        plan.max_issues = 80
        plan.expansion_budget = 3
        plan.diversity_target = 5
        plan.precision_target = 0.6
    elif query_scope.scope == "ambiguous":
        plan.max_repos = 0
        plan.max_issues = 0
        plan.expansion_budget = 0
        plan.repo_search_queries = []
        plan.global_issue_queries = []
        plan.repo_issue_queries = []
        plan.discussion_queries = []
    return plan


def generate_search_plan(
    user_query: str,
    intent: SearchIntent | None = None,
    query_scope: QueryScopeDetection | None = None,
    *,
    use_llm_seeds: bool = True,
) -> SearchPlan:
    """Generate a bounded SearchPlan for arbitrary product queries."""
    intent = intent or detect_search_intent(user_query)
    topic = query_scope.normalized_query if query_scope and query_scope.normalized_query else intent.normalized_topic or user_query.strip() or "GitHub developer tooling"
    seed_payload = (
        _llm_seed_payload(topic, intent, query_scope)
        if use_llm_seeds
        else None
    ) or _coerce_seed_payload({}, topic, intent, query_scope)
    seed_terms = seed_payload["seed_terms"]
    synonyms = seed_payload["synonyms"]
    repo_hints = seed_payload["repo_hints"]
    topic_first_terms = [topic] + synonyms + [term for term in seed_terms if term.lower() != topic.lower()]
    repo_query_terms = _clean_terms(topic_first_terms)[: MAX_SEED_TERMS + MAX_SYNONYMS]
    issue_query_terms = _issue_query_terms(topic, seed_terms, synonyms, query_scope)

    if repo_hints and intent.intent == "repo":
        repo_search_queries = repo_hints[:MAX_REPO_QUERIES]
        global_issue_queries = [
            f"repo:{repo_hints[0]} {pattern} type:issue"
            for pattern in REPO_ISSUE_PATTERNS
        ][:MAX_GLOBAL_ISSUE_QUERIES]
    else:
        repo_search_queries = _format_patterns(REPO_SEARCH_PATTERNS, repo_query_terms, limit=MAX_REPO_QUERIES)
        global_issue_queries = _format_patterns(GLOBAL_ISSUE_PATTERNS, issue_query_terms, limit=MAX_INITIAL_GLOBAL_ISSUE_QUERIES)

    discussion_queries = [
        query.replace("type:issue", "type:discussion")
        for query in global_issue_queries[:MAX_DISCUSSION_QUERIES]
    ]

    plan = SearchPlan(
        topic=topic,
        intent=intent.intent,
        seed_terms=seed_terms,
        synonyms=synonyms,
        repo_hints=repo_hints,
        repo_search_queries=repo_search_queries,
        global_issue_queries=global_issue_queries,
        repo_issue_queries=list(REPO_ISSUE_PATTERNS),
        discussion_queries=discussion_queries,
        positive_signals=_dedupe(list(POSITIVE_SIGNAL_TERMS)),
        negative_signals=_dedupe(list(NEGATIVE_SIGNAL_TERMS)),
    )
    return _apply_scope_settings(plan, query_scope)


def build_search_plan(topic: str, *, iteration_count: int = 0) -> SearchPlan:
    """Backwards-compatible deterministic-ish entry point."""
    plan = generate_search_plan(topic)
    if iteration_count > 0:
        expanded = plan.model_copy(deep=True)
        terms = _dedupe([expanded.topic] + expanded.synonyms + expanded.seed_terms)[:MAX_SEED_TERMS]
        expanded.global_issue_queries = _dedupe(
            expanded.global_issue_queries
            + _format_patterns(EXPANSION_PATTERNS, terms, limit=MAX_GLOBAL_ISSUE_QUERIES)
        )[:MAX_GLOBAL_ISSUE_QUERIES]
        expanded.expansion_budget = max(0, expanded.expansion_budget - iteration_count)
        return expanded
    return plan


def expand_search_plan(plan: SearchPlan, *, iteration_count: int) -> SearchPlan:
    """Bounded expansion used by the adaptive expander."""
    expanded = plan.model_copy(deep=True)
    if expanded.expansion_budget <= 0:
        return expanded
    terms = _dedupe([expanded.topic] + expanded.synonyms + expanded.seed_terms)[:MAX_SEED_TERMS]
    expanded.global_issue_queries = _dedupe(
        expanded.global_issue_queries
        + _format_patterns(EXPANSION_PATTERNS, terms, limit=MAX_GLOBAL_ISSUE_QUERIES)
    )[:MAX_GLOBAL_ISSUE_QUERIES]
    expanded.discussion_queries = _dedupe(
        expanded.discussion_queries
        + [query.replace("type:issue", "type:discussion") for query in expanded.global_issue_queries[:MAX_DISCUSSION_QUERIES]]
    )[:MAX_DISCUSSION_QUERIES]
    expanded.expansion_budget = max(0, expanded.expansion_budget - 1)
    return expanded
