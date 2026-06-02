"""Opportunity card generation node with mock and optional real LLM mode."""

from __future__ import annotations

import time
from pathlib import Path
import re
from typing import Any

from app.config import get_settings
from app.context.builders import build_context_packet
from app.graph.state import GraphState
from app.harness.llm_runner import LLMRunner
from app.harness.trace_logger import JsonTraceLogger
from app.services.llm_client import LLMClient, parse_json_object


PRODUCT_FORM_BY_COST = {
    "low": "Hosted SaaS",
    "medium": "Plugin",
    "high": "Consulting",
}

PRODUCT_FORMS = {"Hosted SaaS", "Plugin", "Template", "Managed Service", "Consulting", "Watch"}
MIGRATION_COSTS = {"low", "medium", "high"}

SCORE_KEYS = {
    "pain_intensity",
    "evidence_strength",
    "repetition",
    "commercial_gap",
    "migration_cost",
    "build_feasibility",
    "distribution_feasibility",
    "overall",
}

OPPORTUNITY_CARD_SCHEMA = {
    "opportunity_id": "str",
    "title": "str",
    "target_user": "str",
    "source_repos": "list[str]",
    "pain_summary": "str",
    "commercial_gap": "str",
    "migration_cost": "low | medium | high",
    "product_form": "str",
    "mvp_features": "list[str]",
    "pricing_hypothesis": "str",
    "first_users": "list[str]",
    "validation_actions": "list[str]",
    "risks": "list[str]",
    "score_json": "dict[str, int]",
    "evidence_ids": "list[str]",
}


OPPORTUNITY_GAP_BUDGET_BY_SCOPE = {
    "repo_specific": 5,
    "focused": 6,
    "broad": 8,
    "ambiguous": 0,
}


def _load_prompt() -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / "opportunity_generator.txt"
    return path.read_text(encoding="utf-8")


def _clean_evidence_ids(raw_ids: Any, allowed: list[str]) -> list[str]:
    if not isinstance(raw_ids, list):
        raw_ids = []
    allowed_set = set(allowed)
    cleaned = [str(item) for item in raw_ids if str(item) in allowed_set]
    if not cleaned:
        cleaned = list(allowed)
    return list(dict.fromkeys(cleaned))


def _as_string_list(value: Any, fallback: list[str] | None = None) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return fallback or []


def _score_json(value: Any, evidence_count: int, migration_cost: str) -> dict[str, int]:
    scores = value if isinstance(value, dict) else {}
    migration_score = {"low": 80, "medium": 60, "high": 35}.get(migration_cost, 50)
    defaults = {
        "pain_intensity": 60,
        "evidence_strength": min(100, evidence_count * 25),
        "repetition": min(100, evidence_count * 18),
        "commercial_gap": 60,
        "migration_cost": migration_score,
        "build_feasibility": migration_score,
        "distribution_feasibility": 55,
        "overall": 60,
    }
    out: dict[str, int] = {}
    for key in SCORE_KEYS:
        try:
            raw = int(scores.get(key, defaults[key]))
        except (TypeError, ValueError):
            raw = defaults[key]
        out[key] = max(0, min(100, raw))
    if "overall" not in scores:
        out["overall"] = int(sum(out[k] for k in SCORE_KEYS if k != "overall") / 7)
    return out


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
            }
        )
    return summaries


def _related_pain_points(state: GraphState, evidence_ids: list[str]) -> list[dict]:
    evidence_set = set(evidence_ids)
    return [
        {
            "pain_id": pain.get("pain_id"),
            "evidence_id": pain.get("evidence_id"),
            "pain_type": pain.get("pain_type"),
            "complaint": pain.get("complaint"),
            "persona": pain.get("persona"),
            "context": pain.get("context"),
            "business_signal": pain.get("business_signal"),
        }
        for pain in state.get("pain_points") or []
        if pain.get("evidence_id") in evidence_set
    ]


def _source_repos_from_evidence(state: GraphState, evidence_ids: list[str]) -> list[str]:
    by_id = {item.get("evidence_id"): item for item in state.get("evidence_items") or []}
    repos = []
    for evidence_id in evidence_ids:
        item = by_id.get(evidence_id)
        if not item:
            continue
        repo = f"{item.get('repo_owner')}/{item.get('repo_name')}"
        if repo != "/":
            repos.append(repo)
    return list(dict.fromkeys(repos))


def _github_authors_from_evidence(state: GraphState, evidence_ids: list[str]) -> list[str]:
    by_id = {item.get("evidence_id"): item for item in state.get("evidence_items") or []}
    users = []
    for evidence_id in evidence_ids:
        item = by_id.get(evidence_id)
        if item and item.get("author_login"):
            users.append(str(item["author_login"]))
    return list(dict.fromkeys(users))


def _card_text_key(card: dict) -> str:
    text = " ".join(
        str(card.get(key) or "")
        for key in ["title", "pain_summary", "commercial_gap", "problem"]
    ).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def dedupe_opportunity_cards(cards: list[dict]) -> list[dict]:
    """Remove duplicate opportunity cards while preserving order."""
    seen_evidence_sets: set[tuple[str, ...]] = set()
    seen_text_keys: set[str] = set()
    deduped: list[dict] = []
    for card in cards:
        evidence_key = tuple(sorted(str(item) for item in card.get("evidence_ids", []) if str(item).strip()))
        text_key = _card_text_key(card)
        if evidence_key and evidence_key in seen_evidence_sets:
            continue
        if text_key and text_key in seen_text_keys:
            continue
        if evidence_key:
            seen_evidence_sets.add(evidence_key)
        if text_key:
            seen_text_keys.add(text_key)
        deduped.append(card)
    return deduped


def _gap_sort_key(gap: dict) -> tuple[int, float, int, int, int]:
    evidence_count = len(gap.get("evidence_ids") or [])
    confidence = float(gap.get("confidence") or 0.5)
    migration_score = {"low": 3, "medium": 2, "high": 0}.get(str(gap.get("migration_cost") or "").lower(), 1)
    saas_score = 0 if gap.get("consulting_vs_saas") == "consulting_like" else 1
    product_score = 0 if gap.get("best_product_form") == "Watch" else 1
    return (evidence_count, confidence, migration_score, saas_score, product_score)


def select_gap_candidates(state: GraphState, gaps: list[dict]) -> list[dict]:
    """Keep only the strongest commercial gaps before expensive card generation."""
    plan = state.get("search_plan") or {}
    scope = str(plan.get("query_scope") or "")
    budget = OPPORTUNITY_GAP_BUDGET_BY_SCOPE.get(scope, 6)
    eligible = [
        gap
        for gap in gaps
        if len(gap.get("evidence_ids") or []) >= 3
        and not (
            str(gap.get("migration_cost") or "").lower() == "high"
            and gap.get("consulting_vs_saas") == "consulting_like"
            and float(gap.get("confidence") or 0) < 0.85
        )
    ]
    return sorted(eligible, key=_gap_sort_key, reverse=True)[: max(0, budget)]


def parse_opportunity_card_response(response: str | dict[str, Any], gap: dict, state: GraphState | None = None) -> dict:
    """Validate and normalize a real LLM opportunity card response."""
    data = parse_json_object(response)
    allowed_ids = [str(item) for item in gap.get("evidence_ids", [])]
    evidence_ids = _clean_evidence_ids(data.get("evidence_ids"), allowed_ids)
    migration_cost = str(data.get("migration_cost") or gap.get("migration_cost") or "medium").strip().lower()
    if migration_cost not in MIGRATION_COSTS:
        migration_cost = "medium"
    product_form = str(data.get("product_form") or data.get("best_product_form") or gap.get("best_product_form") or PRODUCT_FORM_BY_COST.get(migration_cost, "Watch")).strip()
    if product_form not in PRODUCT_FORMS:
        product_form = PRODUCT_FORM_BY_COST.get(migration_cost, "Watch")
    source_repos = _as_string_list(data.get("source_repos"))
    first_users = _as_string_list(data.get("first_users"))
    if state is not None:
        source_repos = source_repos or _source_repos_from_evidence(state, evidence_ids)
        first_users = first_users or _github_authors_from_evidence(state, evidence_ids)
    pricing_hypothesis = str(data.get("pricing_hypothesis") or "Hypothesis: teams may pay for a production workflow layer if validation interviews confirm budget.").strip()
    if not any(word in pricing_hypothesis.lower() for word in ["hypothesis", "assume", "estimated", "estimate", "could", "may", "likely", "proposed"]):
        pricing_hypothesis = f"Hypothesis: {pricing_hypothesis}"
    card = {
        "opportunity_id": str(data.get("opportunity_id") or f"opp_{gap.get('gap_id')}"),
        "cluster_id": gap.get("cluster_id"),
        "title": str(data.get("title") or gap.get("theme") or gap.get("commercial_gap_type") or "GitHub workflow opportunity").strip(),
        "target_user": str(data.get("target_user") or gap.get("who_would_pay") or "engineering teams adopting GitHub OSS in production").strip(),
        "source_repos": source_repos,
        "pain_summary": str(data.get("pain_summary") or gap.get("gap_summary") or "").strip(),
        "commercial_gap": str(data.get("commercial_gap") or gap.get("gap_summary") or gap.get("commercial_gap") or "").strip(),
        "problem": str(data.get("commercial_gap") or gap.get("gap_summary") or gap.get("commercial_gap") or "").strip(),
        "migration_cost": migration_cost,
        "product_form": product_form,
        "best_product_form": product_form,
        "mvp_features": _as_string_list(data.get("mvp_features"), ["Evidence dashboard", "Workflow integration", "Validation report"]),
        "pricing_hypothesis": pricing_hypothesis,
        "first_users": first_users,
        "validation_actions": _as_string_list(
            data.get("validation_actions"),
            ["Contact linked GitHub issue authors and ask for a 20-minute workflow interview."],
        ),
        "risks": _as_string_list(data.get("risks"), ["Evidence may indicate support pain rather than buyer urgency."]),
        "score_json": _score_json(data.get("score_json"), len(evidence_ids), migration_cost),
        "evidence_ids": evidence_ids,
        "evidence_urls": [],
        "weak_card": len(evidence_ids) < 3,
    }
    return card


def _trace_llm_call(
    state: GraphState,
    *,
    gap_id: str,
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
        node_name="opportunity_generate.llm",
        input_data={"gap_id": gap_id},
        output_data=output_data,
        latency_ms=latency_ms,
        errors=errors,
        prompt_version="opportunity_generator:real-v1",
        model=model,
        is_mock=False,
    )


def _card_with_llm(state: GraphState, gap: dict, client: LLMClient) -> tuple[dict | None, str | None]:
    gap_id = str(gap.get("gap_id"))
    evidence_ids = [str(item) for item in gap.get("evidence_ids", [])]
    packet = build_context_packet(
        node_name="opportunity_generate",
        goal="Generate one evidence-grounded opportunity card from one commercial gap.",
        input_items=[
            {
                "commercial_gap": gap,
                "pain_points": _related_pain_points(state, evidence_ids),
                "evidence_summaries": _evidence_summaries(state, evidence_ids),
                "source_repos": _source_repos_from_evidence(state, evidence_ids),
            }
        ],
        evidence_ids=evidence_ids,
        output_schema=OPPORTUNITY_CARD_SCHEMA,
        prompt_version="opportunity_generator:real-v1",
    )
    prompt = _load_prompt() + "\n\nContextPacket:\n" + packet.model_dump_json(indent=2)
    start = time.perf_counter()
    try:
        response = client.structured(prompt, OPPORTUNITY_CARD_SCHEMA, system_prompt="You are a strict JSON opportunity-card generator.")
        parsed = parse_opportunity_card_response(response, gap, state)
        _trace_llm_call(
            state,
            gap_id=gap_id,
            output_data=parsed,
            latency_ms=(time.perf_counter() - start) * 1000,
            errors=[],
            model=client.model,
        )
        return parsed, None
    except Exception as exc:
        error = f"opportunity_generate {gap_id}: {type(exc).__name__}: {exc}"
        _trace_llm_call(
            state,
            gap_id=gap_id,
            output_data={},
            latency_ms=(time.perf_counter() - start) * 1000,
            errors=[error],
            model=client.model,
        )
        return None, error


def opportunity_generate(state: GraphState) -> GraphState:
    settings = get_settings()
    errors = list(state.get("errors") or [])
    use_real_llm = (not settings.mock_mode) and bool(settings.llm_api_key)

    if use_real_llm:
        gaps = select_gap_candidates(state, state.get("commercial_gaps") or [])
        runner = LLMRunner(max_concurrency=settings.max_llm_concurrency)
        with LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            mock_mode=False,
            cache_enabled=settings.llm_cache_enabled,
        ) as client:
            results = runner.run_many(
                gaps,
                lambda gap: _card_with_llm(state, gap, client),
            )
        cards = []
        for gap, (parsed, error) in zip(gaps, results):
            if parsed is not None:
                cards.append(parsed)
            else:
                errors.append(error or f"opportunity_generate {gap.get('gap_id')} failed")
        return {
            **state,
            "opportunity_gap_candidates": gaps,
            "opportunity_gap_budget": len(gaps),
            "opportunity_cards": dedupe_opportunity_cards(cards),
            "errors": errors,
        }

    cards = []
    for idx, gap in enumerate(state.get("commercial_gaps") or [], start=1):
        evidence_ids = list(dict.fromkeys(gap.get("evidence_ids", [])))[:6]
        cards.append(
            {
                "opportunity_id": f"opp_{idx}",
                "cluster_id": gap.get("cluster_id"),
                "title": gap["theme"],
                "problem": gap["commercial_gap"],
                "target_user": "engineering teams adopting GitHub OSS in production",
                "best_product_form": PRODUCT_FORM_BY_COST.get(gap["migration_cost"], "Watch"),
                "migration_cost": gap["migration_cost"],
                "evidence_ids": evidence_ids,
                "evidence_urls": [],
                "why_now": "The repo has repeated production workflow issues across active users.",
            }
        )
    return {**state, "opportunity_cards": dedupe_opportunity_cards(cards)}
