"""Debate node with mock subgraph and optional real structured reviews."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.context.builders import build_context_packet
from app.graph.debate_graph import run_debate_graph
from app.graph.state import GraphState
from app.harness.llm_runner import LLMRunner
from app.harness.trace_logger import JsonTraceLogger
from app.services.llm_client import LLMClient, parse_json_object


AGENTS = {
    "PM": "pm_agent.txt",
    "Engineer": "engineer_agent.txt",
    "Founder": "founder_agent.txt",
    "Skeptic": "skeptic_agent.txt",
}

RECOMMENDATIONS = {"build", "validate", "watch", "reject"}
AGENT_REVIEW_FIELDS = {
    "opportunity_id",
    "agent",
    "score",
    "key_argument",
    "main_risk",
    "recommendation",
}

AGENT_REVIEW_SCHEMA = {
    "opportunity_id": "str",
    "agent": "PM | Engineer | Founder | Skeptic",
    "score": "int 0..10",
    "key_argument": "str",
    "main_risk": "str",
    "recommendation": "build | validate | watch | reject",
}


def _load_prompt(file_name: str) -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / file_name
    return path.read_text(encoding="utf-8")


def _coerce_score(value: Any) -> int:
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        return 5
    return max(0, min(10, score))


def _safe_text(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def parse_agent_review_response(response: str | dict[str, Any], card: dict, agent: str) -> dict:
    """Validate and normalize a structured agent review."""
    data = parse_json_object(response)
    opportunity_id = str(card.get("opportunity_id") or data.get("opportunity_id") or "")
    recommendation = str(data.get("recommendation") or "watch").strip().lower()
    if recommendation not in RECOMMENDATIONS:
        recommendation = "watch"
    review = {
        # Always bind the review to the current validated card. This prevents a
        # malformed LLM response from leaking reviews onto the wrong card.
        "opportunity_id": opportunity_id,
        "agent": agent,
        "score": _coerce_score(data.get("score")),
        "key_argument": _safe_text(data.get("key_argument"), "No supported argument provided."),
        "main_risk": _safe_text(data.get("main_risk"), "No supported risk provided."),
        "recommendation": recommendation,
    }
    return {key: review[key] for key in AGENT_REVIEW_FIELDS}


def _evidence_summaries(state: GraphState, evidence_ids: list[str], max_items: int = 6) -> list[dict]:
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
                "title": item.get("title", "")[:220],
                "body_excerpt": item.get("body", "")[:420],
                "author_login": item.get("author_login"),
            }
        )
    return summaries


def _trace_llm_call(
    state: GraphState,
    *,
    opportunity_id: str,
    agent: str,
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
        node_name="debate.llm",
        input_data={"opportunity_id": opportunity_id, "agent": agent},
        output_data=output_data,
        latency_ms=latency_ms,
        errors=errors,
        prompt_version=f"{agent.lower()}_agent:real-v1",
        model=model,
        is_mock=False,
    )


def _review_with_llm(state: GraphState, card: dict, agent: str, client: LLMClient) -> tuple[dict | None, str | None]:
    opportunity_id = str(card.get("opportunity_id"))
    evidence_ids = [str(item) for item in card.get("evidence_ids", [])]
    packet = build_context_packet(
        node_name="debate",
        goal=f"Single-pass structured {agent} review for one opportunity card.",
        input_items=[
            {
                "opportunity_card": card,
                "evidence_summaries": _evidence_summaries(state, evidence_ids),
            }
        ],
        evidence_ids=evidence_ids,
        output_schema=AGENT_REVIEW_SCHEMA,
        prompt_version=f"{agent.lower()}_agent:real-v1",
    )
    prompt = _load_prompt(AGENTS[agent]) + "\n\nContextPacket:\n" + packet.model_dump_json(indent=2)
    start = time.perf_counter()
    try:
        response = client.structured(prompt, AGENT_REVIEW_SCHEMA, system_prompt=f"You are the {agent} reviewer. Return JSON only.")
        parsed = parse_agent_review_response(response, card, agent)
        _trace_llm_call(
            state,
            opportunity_id=opportunity_id,
            agent=agent,
            output_data=parsed,
            latency_ms=(time.perf_counter() - start) * 1000,
            errors=[],
            model=client.model,
        )
        return parsed, None
    except Exception as exc:
        error = f"debate {opportunity_id} {agent}: {type(exc).__name__}: {exc}"
        _trace_llm_call(
            state,
            opportunity_id=opportunity_id,
            agent=agent,
            output_data={},
            latency_ms=(time.perf_counter() - start) * 1000,
            errors=[error],
            model=client.model,
        )
        return None, error


def debate(state: GraphState) -> GraphState:
    settings = get_settings()
    errors = list(state.get("errors") or [])
    use_real_llm = (not settings.mock_mode) and bool(settings.llm_api_key)

    if use_real_llm:
        cards = state.get("validated_cards") or []
        if not cards:
            return {**state, "agent_reviews": [], "errors": errors}
        tasks = [(card, agent) for card in cards for agent in AGENTS]
        runner = LLMRunner(max_concurrency=settings.max_llm_concurrency)
        with LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            mock_mode=False,
            cache_enabled=settings.llm_cache_enabled,
        ) as client:
            results = runner.run_many(
                tasks,
                lambda item: _review_with_llm(state, item[0], item[1], client),
            )
        reviews: list[dict] = []
        for (card, agent), (review, error) in zip(tasks, results):
            if review is not None:
                reviews.append(review)
            else:
                errors.append(error or f"debate {card.get('opportunity_id')} {agent} failed")
        return {**state, "agent_reviews": reviews, "errors": errors}

    reviews: list[dict] = []
    decisions: list[dict] = []
    for card in state.get("validated_cards") or []:
        result = run_debate_graph(card)
        for raw_review in result.get("agent_reviews", []):
            agent = str(raw_review.get("agent") or "Reviewer")
            reviews.append(parse_agent_review_response(raw_review, card, agent))
        decision = result.get("final_decision", {})
        if decision:
            decisions.append({"opportunity_id": card["opportunity_id"], **decision})
    return {**state, "agent_reviews": reviews, "final_decisions": decisions}
