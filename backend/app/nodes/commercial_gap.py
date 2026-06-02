"""Commercial gap analysis node with mock and optional real LLM mode."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.context.builders import build_context_packet
from app.graph.state import GraphState
from app.harness.llm_runner import LLMRunner
from app.harness.trace_logger import JsonTraceLogger
from app.services.llm_client import LLMClient, parse_json_object


COMMERCIAL_GAP_TYPES = {
    "Hosted SaaS gap",
    "Managed deployment gap",
    "Plugin / integration gap",
    "No-code UI gap",
    "Enterprise dashboard gap",
    "Monitoring / evaluation dashboard gap",
    "Template / boilerplate gap",
    "Compliance / security layer gap",
    "Vertical workflow gap",
    "unclear",
}

PRODUCT_FORMS = {"Hosted SaaS", "Plugin", "Template", "Managed Service", "Consulting", "Watch"}
MIGRATION_COSTS = {"low", "medium", "high"}
CONSULTING_VS_SAAS = {"saas_possible", "consulting_like", "unclear"}

COMMERCIAL_GAP_SCHEMA = {
    "gap_id": "str",
    "cluster_id": "str",
    "commercial_gap_type": "str",
    "gap_summary": "str",
    "why_open_source_is_not_enough": "str",
    "who_would_pay": "str",
    "best_product_form": "str",
    "migration_cost": "low | medium | high",
    "migration_cost_reason": "str",
    "consulting_vs_saas": "str",
    "why_now": "str",
    "confidence": "float 0..1",
    "evidence_ids": "list[str]",
}


COMMERCIAL_CLUSTER_BUDGET_BY_SCOPE = {
    "repo_specific": 5,
    "focused": 6,
    "broad": 8,
    "ambiguous": 0,
}


def _migration_cost(theme: str) -> tuple[str, str]:
    lowered = theme.lower()
    if any(term in lowered for term in ["evaluation", "observability", "workflow"]):
        return "low", "wrapper/plugin/dashboard/hosted layer can solve it"
    if any(term in lowered for term in ["integration", "enterprise", "permission"]):
        return "medium", "SDK/data integration needed"
    return "high", "requires rewriting customer architecture; likely consulting, not SaaS"


def _load_prompt() -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / "commercial_gap.txt"
    return path.read_text(encoding="utf-8")


def _coerce_float(value: Any, default: float = 0.5) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, score))


def _clean_evidence_ids(raw_ids: Any, allowed: list[str]) -> list[str]:
    if not isinstance(raw_ids, list):
        raw_ids = []
    allowed_set = set(allowed)
    cleaned = [str(item) for item in raw_ids if str(item) in allowed_set]
    if not cleaned:
        cleaned = list(allowed)
    return list(dict.fromkeys(cleaned))


def _evidence_summaries(state: GraphState, evidence_ids: list[str], max_items: int = 8) -> list[dict]:
    by_id = {item.get("evidence_id"): item for item in state.get("evidence_items") or []}
    summaries = []
    for evidence_id in evidence_ids[:max_items]:
        item = by_id.get(evidence_id)
        if not item:
            continue
        summaries.append(
            {
                "evidence_id": evidence_id,
                "source_url": item.get("source_url"),
                "repo": f"{item.get('repo_owner')}/{item.get('repo_name')}",
                "title": item.get("title", "")[:240],
                "body_excerpt": item.get("body", "")[:500],
                "author_login": item.get("author_login"),
                "comment_count": item.get("comment_count"),
            }
        )
    return summaries


def _related_pain_points(state: GraphState, cluster: dict) -> list[dict]:
    pain_ids = set(cluster.get("pain_ids") or [])
    evidence_ids = set(cluster.get("evidence_ids") or [])
    pains = []
    for pain in state.get("pain_points") or []:
        if pain.get("pain_id") in pain_ids or pain.get("evidence_id") in evidence_ids:
            pains.append(
                {
                    "pain_id": pain.get("pain_id"),
                    "evidence_id": pain.get("evidence_id"),
                    "pain_type": pain.get("pain_type"),
                    "complaint": pain.get("complaint"),
                    "persona": pain.get("persona"),
                    "context": pain.get("context"),
                    "business_signal": pain.get("business_signal"),
                    "supporting_quote": pain.get("supporting_quote"),
                }
            )
    return pains


def _source_repos(state: GraphState, evidence_ids: list[str]) -> list[dict]:
    by_id = {item.get("evidence_id"): item for item in state.get("evidence_items") or []}
    repos: dict[str, dict] = {}
    for evidence_id in evidence_ids:
        item = by_id.get(evidence_id)
        if not item:
            continue
        repo_name = f"{item.get('repo_owner')}/{item.get('repo_name')}"
        repos[repo_name] = {"repo": repo_name, "repo_url": item.get("repo_url")}
    return list(repos.values())


def _cluster_sort_key(cluster: dict) -> tuple[int, float, float]:
    return (
        int(cluster.get("evidence_count") or len(cluster.get("evidence_ids") or [])),
        float(cluster.get("repetition_score") or 0),
        float(cluster.get("severity_score") or 0),
    )


def _select_cluster_candidates(state: GraphState, clusters: list[dict]) -> list[dict]:
    plan = state.get("search_plan") or {}
    scope = str(plan.get("query_scope") or "")
    budget = COMMERCIAL_CLUSTER_BUDGET_BY_SCOPE.get(scope, 6)
    sorted_clusters = sorted(clusters, key=_cluster_sort_key, reverse=True)
    return sorted_clusters[: max(0, budget)]


def parse_commercial_gap_response(response: str | dict[str, Any], cluster: dict) -> dict:
    """Validate and normalize a real LLM commercial gap response."""
    data = parse_json_object(response)
    allowed_ids = [str(item) for item in cluster.get("evidence_ids", [])]
    evidence_ids = _clean_evidence_ids(data.get("evidence_ids"), allowed_ids)
    gap_type = str(data.get("commercial_gap_type") or "unclear").strip()
    if gap_type not in COMMERCIAL_GAP_TYPES:
        gap_type = "unclear"
    migration_cost = str(data.get("migration_cost") or "").strip().lower()
    if migration_cost not in MIGRATION_COSTS:
        migration_cost, default_reason = _migration_cost(cluster.get("theme", ""))
    else:
        default_reason = ""
    product_form = str(data.get("best_product_form") or "Watch").strip()
    if product_form not in PRODUCT_FORMS:
        product_form = "Watch"
    consulting_vs_saas = str(data.get("consulting_vs_saas") or "unclear").strip()
    if consulting_vs_saas not in CONSULTING_VS_SAAS:
        consulting_vs_saas = "unclear"
    return {
        "gap_id": str(data.get("gap_id") or f"gap_{cluster.get('cluster_id')}"),
        "cluster_id": str(data.get("cluster_id") or cluster.get("cluster_id")),
        "theme": cluster.get("theme"),
        "commercial_gap_type": gap_type,
        "gap_summary": str(data.get("gap_summary") or "Potential production workflow gap around this open-source project.").strip(),
        "commercial_gap": str(data.get("gap_summary") or data.get("commercial_gap") or "Potential production workflow gap around this open-source project.").strip(),
        "why_open_source_is_not_enough": str(data.get("why_open_source_is_not_enough") or "").strip(),
        "who_would_pay": str(data.get("who_would_pay") or "Teams adopting the project in production").strip(),
        "best_product_form": product_form,
        "migration_cost": migration_cost,
        "migration_cost_reason": str(data.get("migration_cost_reason") or default_reason).strip(),
        "consulting_vs_saas": consulting_vs_saas,
        "why_now": str(data.get("why_now") or "").strip(),
        "confidence": _coerce_float(data.get("confidence")),
        "evidence_ids": evidence_ids,
    }


def _trace_llm_call(
    state: GraphState,
    *,
    cluster_id: str,
    output_data: dict,
    latency_ms: float,
    errors: list[str],
    model: str,
) -> None:
    logger = state.get("_trace_logger")
    if not isinstance(logger, JsonTraceLogger):
        return
    logger.log(
        run_id=state.get("run_id", "local"),
        node_name="commercial_gap.llm",
        input_data={"cluster_id": cluster_id},
        output_data=output_data,
        latency_ms=latency_ms,
        errors=errors,
        prompt_version="commercial_gap:real-v1",
        model=model,
        is_mock=False,
    )


def _gap_with_llm(state: GraphState, cluster: dict, client: LLMClient) -> tuple[dict | None, str | None]:
    cluster_id = str(cluster.get("cluster_id"))
    evidence_ids = [str(item) for item in cluster.get("evidence_ids", [])]
    packet = build_context_packet(
        node_name="commercial_gap",
        goal="Detect a commercial gap from one pain cluster and related evidence.",
        input_items=[
            {
                "cluster": cluster,
                "pain_points": _related_pain_points(state, cluster),
                "evidence_summaries": _evidence_summaries(state, evidence_ids),
                "source_repos": _source_repos(state, evidence_ids),
            }
        ],
        evidence_ids=evidence_ids,
        output_schema=COMMERCIAL_GAP_SCHEMA,
        prompt_version="commercial_gap:real-v1",
    )
    prompt = _load_prompt() + "\n\nContextPacket:\n" + packet.model_dump_json(indent=2)
    start = time.perf_counter()
    try:
        response = client.structured(prompt, COMMERCIAL_GAP_SCHEMA, system_prompt="You are a strict JSON commercial-gap analyst.")
        parsed = parse_commercial_gap_response(response, cluster)
        _trace_llm_call(
            state,
            cluster_id=cluster_id,
            output_data=parsed,
            latency_ms=(time.perf_counter() - start) * 1000,
            errors=[],
            model=client.model,
        )
        return parsed, None
    except Exception as exc:
        error = f"commercial_gap {cluster_id}: {type(exc).__name__}: {exc}"
        _trace_llm_call(
            state,
            cluster_id=cluster_id,
            output_data={},
            latency_ms=(time.perf_counter() - start) * 1000,
            errors=[error],
            model=client.model,
        )
        return None, error


def commercial_gap(state: GraphState) -> GraphState:
    settings = get_settings()
    errors = list(state.get("errors") or [])
    use_real_llm = (not settings.mock_mode) and bool(settings.llm_api_key)

    if use_real_llm:
        clusters = _select_cluster_candidates(state, state.get("pain_clusters") or [])
        runner = LLMRunner(max_concurrency=settings.max_llm_concurrency)
        with LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            mock_mode=False,
            cache_enabled=settings.llm_cache_enabled,
        ) as client:
            results = runner.run_many(
                clusters,
                lambda cluster: _gap_with_llm(state, cluster, client),
            )
        gaps = []
        for cluster, (parsed, error) in zip(clusters, results):
            if parsed is not None:
                gaps.append(parsed)
            else:
                errors.append(error or f"commercial_gap {cluster.get('cluster_id')} failed")
        return {
            **state,
            "commercial_gap_candidate_clusters": clusters,
            "commercial_gap_cluster_budget": len(clusters),
            "commercial_gaps": gaps,
            "errors": errors,
        }

    gaps = []
    for cluster in state.get("pain_clusters") or []:
        migration_cost, rationale = _migration_cost(cluster.get("theme", ""))
        gaps.append(
            {
                "gap_id": f"gap_{cluster['cluster_id']}",
                "cluster_id": cluster["cluster_id"],
                "theme": cluster["theme"],
                "evidence_ids": cluster.get("evidence_ids", []),
                "migration_cost": migration_cost,
                "migration_cost_reason": rationale,
                "commercial_gap": "Open-source users need a production-ready layer around the project.",
            }
        )
    return {**state, "commercial_gaps": gaps}
