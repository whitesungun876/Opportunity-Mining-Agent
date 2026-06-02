"""Cheap opportunity-fit preflight before running the full graph."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.nodes.evidence_quality_rank import evidence_quality_rank
from app.nodes.github_search_orchestrator import github_search_orchestrator
from app.nodes.signal_diagnostics import diagnose_signal
from app.search.intent import detect_intent_rules
from app.search.planner import generate_search_plan
from app.search.scope import detect_query_scope_rules
from app.services.evidence_normalizer import normalize_github_issue
from app.services.github_graphql import GitHubGraphQLClient
from app.services.preflight_cache import preflight_cache


PREFLIGHT_ISSUE_BUDGET_BY_SCOPE = {
    "repo_specific": 20,
    "focused": 36,
    "broad": 30,
    "ambiguous": 0,
}

PREFLIGHT_REPO_BUDGET_BY_SCOPE = {
    "repo_specific": 1,
    "focused": 4,
    "broad": 6,
    "ambiguous": 0,
}


VAGUE_TOPIC_ANCHORS = {
    "agent": "AI agent framework",
    "agents": "AI agent framework",
    "ai": "AI developer tools",
    "tool": "developer tools",
    "tools": "developer tools",
    "framework": "open-source framework",
    "frameworks": "open-source frameworks",
    "mcp": "MCP tools",
    "rag": "RAG evaluation",
}


COMMERCIAL_REFINEMENT_PATTERNS = [
    "{anchor} self-hosted deployment blockers",
    "{anchor} enterprise auth permissions audit logs",
    "{anchor} production debugging observability workflow",
    "{anchor} team admin dashboard workflow",
    "{anchor} managed hosted alternative",
]


def _fit_reason(
    *,
    scope: str,
    evidence_count: int,
    strong_count: int,
    repo_count: int,
    fit: str,
) -> str:
    if scope == "ambiguous":
        return "The input is too broad or short to spend a full GitHub + LLM run on."
    if fit == "high":
        return "GitHub already shows enough repeated production or workflow evidence to justify a full run."
    if fit == "medium":
        return "Some useful GitHub signals were found, but strict validation may still return few or no opportunities."
    if evidence_count == 0:
        return "The quick GitHub probe did not find useful source evidence for this query."
    if strong_count == 0:
        return "GitHub evidence exists, but the quick probe found weak production/commercial signals."
    if scope == "focused":
        return "This focused query has limited repeated evidence; broaden it or add an adjacent production pain."
    if repo_count <= 1 and scope != "repo_specific":
        return "Evidence is concentrated in too few repositories, so opportunity validation may be fragile."
    return "The quick probe found insufficient repeated evidence for strict opportunity validation."


def _suggestions(topic: str, scope: str, plan: dict[str, Any], existing: list[str]) -> list[str]:
    base = topic.strip() or "AI developer tools"
    seeds = [str(item) for item in plan.get("seed_terms") or [] if str(item).strip()]
    anchor = _commercial_anchor(seeds[0] if seeds else base)
    suggestions: list[str] = []
    if scope == "focused":
        suggestions.extend(
            [
                f"{anchor} production blocker repeated user pain",
                f"{anchor} self-hosted deployment maintenance",
                f"{anchor} enterprise security compliance workflow",
                f"{anchor} team dashboard audit logs",
                f"{anchor} debugging observability workflow",
            ]
        )
    elif scope == "broad":
        suggestions.extend(_commercial_patterns(anchor))
    elif scope == "repo_specific":
        suggestions.extend(
            [
                f"{base} self-hosted deployment blockers",
                f"{base} enterprise auth permissions",
                f"{base} observability debugging workflow",
                f"{base} admin dashboard team workflow",
                f"{base} managed hosted alternative",
            ]
        )
    else:
        suggestions.extend(_commercial_patterns(anchor))
    suggestions.extend(existing)
    return [item for item in dict.fromkeys(suggestions) if item.strip()][:5]


def _commercial_anchor(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    lower = cleaned.lower()
    if lower in VAGUE_TOPIC_ANCHORS:
        return VAGUE_TOPIC_ANCHORS[lower]
    return cleaned or "AI developer tools"


def _commercial_patterns(anchor: str) -> list[str]:
    return [pattern.format(anchor=anchor) for pattern in COMMERCIAL_REFINEMENT_PATTERNS]


def _estimate(scope: str, fit: str) -> tuple[str, str]:
    if scope == "ambiguous" or fit == "needs_refinement":
        return "low", "none"
    if scope == "repo_specific":
        return "medium", "short"
    if scope == "focused":
        return "medium", "medium"
    return "high", "long"


def _opportunity_fit(scope: str, evidence_count: int, strong_count: int, repo_count: int) -> str:
    if scope == "ambiguous":
        return "needs_refinement"
    if scope == "repo_specific" and evidence_count >= 20 and strong_count >= 8:
        return "high"
    if scope == "broad" and evidence_count >= 30 and strong_count >= 10 and repo_count >= 5:
        return "high"
    if scope == "focused" and evidence_count >= 30 and strong_count >= 10 and repo_count >= 4:
        return "high"
    if evidence_count >= 15 and strong_count >= 4:
        return "medium"
    if scope == "repo_specific" and evidence_count >= 12 and strong_count >= 3:
        return "medium"
    return "low"


def _cheap_plan(topic: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    scope = detect_query_scope_rules(topic)
    intent = detect_intent_rules(scope.normalized_query or topic)
    plan = generate_search_plan(
        scope.normalized_query or topic,
        intent,
        scope,
        use_llm_seeds=False,
    )
    budget = PREFLIGHT_ISSUE_BUDGET_BY_SCOPE.get(scope.scope, 20)
    plan.max_issues = min(plan.max_issues, budget)
    plan.max_repos = min(plan.max_repos, PREFLIGHT_REPO_BUDGET_BY_SCOPE.get(scope.scope, 3))
    plan.expansion_budget = 0
    plan.global_issue_queries = plan.global_issue_queries[:8 if scope.scope == "focused" else 3]
    plan.discussion_queries = plan.discussion_queries[:1]
    return scope.model_dump(), intent.model_dump(), plan.model_dump()


def _probe_evidence(state: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    if settings.mock_mode:
        return github_search_orchestrator(state)  # type: ignore[arg-type]

    plan = state.get("search_plan") or {}
    scope = str(plan.get("query_scope") or "")
    client = GitHubGraphQLClient(
        token=settings.github_token,
        endpoint=settings.github_graphql_url,
        mock_mode=False,
        timeout_seconds=10,
        retry_limit=1,
    )
    errors: list[str] = []
    issues: list[dict[str, Any]] = []

    try:
        if scope == "repo_specific" and plan.get("repo_hints"):
            full_name = str(plan["repo_hints"][0])
            owner, name = full_name.split("/", 1)
            repo = {
                "repo_id": full_name,
                "full_name": full_name,
                "owner": owner,
                "name": name,
                "url": f"https://github.com/{full_name}",
            }
            issues = client.collect_issues_for_repo(repo)[: int(plan.get("max_issues") or 12)]
            evidence = [
                normalize_github_issue(issue, run_id=state.get("run_id", "preflight"), repo=repo, is_mock=False)
                for issue in issues
            ]
        else:
            queries = plan.get("global_issue_queries") or []
            issues = client.search_issues(
                queries,
                per_query=5 if scope == "focused" else 4,
                max_issues=int(plan.get("max_issues") or 12),
            )
            if not issues and scope == "focused":
                fallback_terms = list(dict.fromkeys((plan.get("synonyms") or []) + (plan.get("seed_terms") or [])))[:6]
                fallback_queries = [
                    f"{term} production workflow type:issue"
                    for term in fallback_terms
                    if str(term).strip()
                ] + [
                    f"{term} blocker workaround type:issue"
                    for term in fallback_terms
                    if str(term).strip()
                ]
                issues = client.search_issues(
                    fallback_queries,
                    per_query=5,
                    max_issues=int(plan.get("max_issues") or 12),
                )
            evidence = [
                normalize_github_issue(issue, run_id=state.get("run_id", "preflight"), is_mock=False)
                for issue in issues
            ]
    except Exception as exc:
        errors.append(f"preflight GitHub probe: {type(exc).__name__}: {exc}")
        evidence = []

    return {
        **state,
        "raw_issues": issues,
        "evidence_items": evidence,
        "evidence_pool": evidence,
        "errors": errors,
    }


def run_preflight(topic: str, *, dynamic_search: bool = True) -> dict[str, Any]:
    """Probe query quality without any LLM calls or full graph execution."""
    preflight_id = str(uuid4())
    scope, intent, plan = _cheap_plan(topic)
    if not dynamic_search:
        plan["source"] = "eval_profile"

    state: dict[str, Any] = {
        "run_id": f"preflight_{uuid4()}",
        "user_query": topic,
        "canonical_topic": scope.get("normalized_query") or topic,
        "query_scope": scope,
        "search_intent": intent,
        "search_plan": plan,
        "repo_search_queries": plan.get("repo_search_queries") or [],
        "global_issue_queries": plan.get("global_issue_queries") or [],
        "repo_issue_queries": plan.get("repo_issue_queries") or [],
        "discussion_queries": plan.get("discussion_queries") or [],
        "github_queries": list(dict.fromkeys((plan.get("repo_search_queries") or []) + (plan.get("global_issue_queries") or []))),
        "errors": [],
        "iteration_count": 0,
    }

    if scope.get("refinement_required"):
        fit = "needs_refinement"
        cost, runtime = _estimate(scope["scope"], fit)
        suggested_queries = _suggestions(topic, scope["scope"], plan, scope.get("suggested_queries") or [])
        plan["suggested_queries"] = suggested_queries
        diagnostics = diagnose_signal(state).model_dump()
        return {
            "preflight_id": preflight_id,
            "topic": topic,
            "normalized_topic": scope.get("normalized_query") or topic,
            "query_scope": scope["scope"],
            "opportunity_fit": fit,
            "should_run": False,
            "reason": _fit_reason(scope=scope["scope"], evidence_count=0, strong_count=0, repo_count=0, fit=fit),
            "estimated_cost": cost,
            "estimated_runtime": runtime,
            "evidence_count": 0,
            "strong_evidence_count": 0,
            "repo_count": 0,
            "suggested_queries": suggested_queries,
            "search_plan": plan,
            "signal_diagnostics": diagnostics,
        }

    settings = get_settings()
    if not settings.mock_mode and not settings.github_token:
        fit = "needs_refinement"
        cost, runtime = _estimate(scope["scope"], fit)
        suggested_queries = _suggestions(topic, scope["scope"], plan, scope.get("suggested_queries") or [])
        plan["suggested_queries"] = suggested_queries
        diagnostics = diagnose_signal(state).model_dump()
        return {
            "preflight_id": preflight_id,
            "topic": topic,
            "normalized_topic": scope.get("normalized_query") or topic,
            "query_scope": scope["scope"],
            "opportunity_fit": fit,
            "should_run": False,
            "reason": "Real GitHub mode needs GITHUB_TOKEN before this query can be probed.",
            "estimated_cost": cost,
            "estimated_runtime": runtime,
            "evidence_count": 0,
            "strong_evidence_count": 0,
            "repo_count": 0,
            "suggested_queries": suggested_queries,
            "search_plan": plan,
            "signal_diagnostics": diagnostics,
        }

    try:
        searched = _probe_evidence(state)
        ranked = evidence_quality_rank(searched)  # type: ignore[arg-type]
    except Exception as exc:
        ranked = {**state, "errors": [f"preflight: {type(exc).__name__}: {exc}"], "evidence_items": [], "ranked_evidence_items": []}

    evidence_items = ranked.get("evidence_items") or []
    ranked_items = ranked.get("ranked_evidence_items") or []
    repo_names = {
        str(item.get("repo") or f"{item.get('repo_owner')}/{item.get('repo_name')}")
        for item in evidence_items
        if item.get("repo") or item.get("repo_owner") or item.get("repo_name")
    }
    strong_count = len([item for item in ranked_items if float(item.get("evidence_quality_score") or 0) >= 8])
    evidence_count = len(evidence_items)
    repo_count = len(repo_names)
    fit = _opportunity_fit(scope["scope"], evidence_count, strong_count, repo_count)
    cost, runtime = _estimate(scope["scope"], fit)
    suggested_queries = _suggestions(topic, scope["scope"], plan, scope.get("suggested_queries") or [])
    plan["suggested_queries"] = suggested_queries
    diagnostics = diagnose_signal(ranked).model_dump()
    if fit in {"high", "medium"}:
        diagnostics = {
            **diagnostics,
            "low_signal_type": "unknown",
            "low_signal_stage": "unknown",
            "low_signal_reason": "",
            "suggested_recovery_actions": [],
        }
    warm_state = {
        **ranked,
        "preflight_id": preflight_id,
        "warm_start_evidence": True,
        "query_scope": scope,
        "search_intent": intent,
        "search_plan": plan,
        "repo_search_queries": plan.get("repo_search_queries") or [],
        "global_issue_queries": plan.get("global_issue_queries") or [],
        "repo_issue_queries": plan.get("repo_issue_queries") or [],
        "discussion_queries": plan.get("discussion_queries") or [],
        "github_queries": list(dict.fromkeys((plan.get("repo_search_queries") or []) + (plan.get("global_issue_queries") or []))),
    }
    preflight_cache.set(preflight_id, warm_state)
    return {
        "preflight_id": preflight_id,
        "topic": topic,
        "normalized_topic": scope.get("normalized_query") or topic,
        "query_scope": scope["scope"],
        "opportunity_fit": fit,
        "should_run": fit in {"high", "medium"},
        "reason": _fit_reason(
            scope=scope["scope"],
            evidence_count=evidence_count,
            strong_count=strong_count,
            repo_count=repo_count,
            fit=fit,
        ),
        "estimated_cost": cost,
        "estimated_runtime": runtime,
        "evidence_count": evidence_count,
        "strong_evidence_count": strong_count,
        "repo_count": repo_count,
        "suggested_queries": suggested_queries,
        "search_plan": plan,
        "signal_diagnostics": diagnostics,
    }
