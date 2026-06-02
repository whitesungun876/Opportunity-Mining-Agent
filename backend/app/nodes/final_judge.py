"""Final judge node for main graph."""

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


DECISIONS = {"build", "validate", "watch", "reject"}
MIGRATION_COSTS = {"low", "medium", "high"}
FINAL_DECISION_FIELDS = {
    "opportunity_id",
    "decision",
    "score",
    "best_product_form",
    "migration_cost",
    "reason",
    "top_risks",
    "first_validation_action",
    "decision_confidence",
}

FINAL_JUDGE_SCHEMA = {
    "opportunity_id": "str",
    "decision": "build | validate | watch | reject",
    "score": "int 0..100",
    "best_product_form": "str",
    "migration_cost": "low | medium | high",
    "reason": "str",
    "top_risks": "list[str]",
    "first_validation_action": "str",
    "decision_confidence": "float 0..1",
}


def _load_prompt() -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / "final_judge.txt"
    return path.read_text(encoding="utf-8")


def _coerce_score(value: Any) -> int:
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        return 50
    return max(0, min(100, score))


def _coerce_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, confidence))


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _safe_text(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def parse_final_judge_response(response: str | dict[str, Any], card: dict) -> dict:
    """Validate and normalize a final judge response."""
    data = parse_json_object(response)
    opportunity_id = str(card.get("opportunity_id") or data.get("opportunity_id") or "")
    decision = str(data.get("decision") or "watch").strip().lower()
    if decision not in DECISIONS:
        decision = "watch"
    migration_cost = str(data.get("migration_cost") or card.get("migration_cost") or "medium").strip().lower()
    if migration_cost not in MIGRATION_COSTS:
        migration_cost = "medium"
    evidence_count = len(card.get("evidence_ids") or [])
    if decision == "build" and (card.get("weak_card") or evidence_count < 3):
        decision = "watch"
    normalized = {
        # Always bind the final decision to the current validated card.
        "opportunity_id": opportunity_id,
        "decision": decision,
        "score": _coerce_score(data.get("score")),
        "best_product_form": _safe_text(
            data.get("best_product_form") or card.get("best_product_form") or card.get("product_form"),
            "Watch",
        ),
        "migration_cost": migration_cost,
        "reason": _safe_text(data.get("reason"), "Decision is based on the validated card and available reviews."),
        "top_risks": _as_list(data.get("top_risks")),
        "first_validation_action": str(
            data.get("first_validation_action")
            or (card.get("validation_actions") or ["Contact linked GitHub issue authors for workflow interviews."])[0]
        ).strip(),
        "decision_confidence": _coerce_confidence(data.get("decision_confidence")),
    }
    if not normalized["first_validation_action"]:
        normalized["first_validation_action"] = "Contact linked GitHub issue authors for workflow interviews."
    return {key: normalized[key] for key in FINAL_DECISION_FIELDS}


def _fallback_decision(card: dict, reviews: list[dict], reason_suffix: str = "") -> dict:
    if reviews:
        avg = sum(int(review.get("score", 5)) for review in reviews) / len(reviews)
    else:
        avg = 5.0
    migration_cost = card.get("migration_cost", "medium")
    evidence_count = len(card.get("evidence_ids", []))
    if evidence_count < 3 or card.get("weak_card"):
        decision = "watch"
    elif migration_cost == "high" and avg < 8:
        decision = "watch"
    elif avg >= 8 and migration_cost in {"low", "medium"}:
        decision = "validate"
    elif avg >= 6:
        decision = "validate"
    else:
        decision = "watch"
    risks = [review.get("main_risk", "") for review in reviews if review.get("main_risk")]
    reason = "Deterministic fallback synthesized available reviews."
    if reason_suffix:
        reason += f" {reason_suffix}"
    return {
        "opportunity_id": card.get("opportunity_id"),
        "decision": decision,
        "score": int(max(0, min(100, avg * 10))),
        "best_product_form": card.get("best_product_form") or card.get("product_form") or "Watch",
        "migration_cost": migration_cost,
        "reason": reason,
        "top_risks": risks[:3],
        "first_validation_action": (card.get("validation_actions") or ["Contact linked GitHub issue authors for workflow interviews."])[0],
        "decision_confidence": 0.45 if reason_suffix else 0.6,
    }


def _trace_llm_call(
    state: GraphState,
    *,
    opportunity_id: str,
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
        node_name="final_judge.llm",
        input_data={"opportunity_id": opportunity_id},
        output_data=output_data,
        latency_ms=latency_ms,
        errors=errors,
        prompt_version="final_judge:real-v1",
        model=model,
        is_mock=False,
    )


def _judge_with_llm(state: GraphState, card: dict, reviews: list[dict], client: LLMClient) -> tuple[dict, str | None]:
    opportunity_id = str(card.get("opportunity_id"))
    commercial_context = {
        "buyer_hypothesis": next(
            (item for item in state.get("buyer_hypotheses") or [] if str(item.get("opportunity_id")) == opportunity_id),
            None,
        ),
        "wtp_signals": [
            item for item in state.get("wtp_signals") or [] if str(item.get("opportunity_id")) == opportunity_id
        ],
        "validation_plan": next(
            (item for item in state.get("validation_plans") or [] if str(item.get("opportunity_id")) == opportunity_id),
            None,
        ),
    }
    packet = build_context_packet(
        node_name="final_judge",
        goal="Synthesize structured agent reviews into one final opportunity decision.",
        input_items=[{"opportunity_card": card, "agent_reviews": reviews, "commercial_validation": commercial_context}],
        evidence_ids=[str(item) for item in card.get("evidence_ids", [])],
        output_schema=FINAL_JUDGE_SCHEMA,
        prompt_version="final_judge:real-v1",
    )
    prompt = _load_prompt() + "\n\nContextPacket:\n" + packet.model_dump_json(indent=2)
    start = time.perf_counter()
    try:
        response = client.structured(prompt, FINAL_JUDGE_SCHEMA, system_prompt="You are a strict JSON final judge.")
        parsed = parse_final_judge_response(response, card)
        _trace_llm_call(
            state,
            opportunity_id=opportunity_id,
            output_data=parsed,
            latency_ms=(time.perf_counter() - start) * 1000,
            errors=[],
            model=client.model,
        )
        return parsed, None
    except Exception as exc:
        error = f"final_judge {opportunity_id}: {type(exc).__name__}: {exc}"
        fallback = _fallback_decision(card, reviews, "LLM judge failed.")
        _trace_llm_call(
            state,
            opportunity_id=opportunity_id,
            output_data=fallback,
            latency_ms=(time.perf_counter() - start) * 1000,
            errors=[error],
            model=client.model,
        )
        return fallback, error


def final_judge(state: GraphState) -> GraphState:
    settings = get_settings()
    cards = state.get("validated_cards") or []
    errors = list(state.get("errors") or [])
    if not cards:
        return {**state, "final_decisions": [], "errors": errors}

    if (not settings.mock_mode) and bool(settings.llm_api_key):
        reviews_by_opp: dict[str, list[dict]] = {}
        for review in state.get("agent_reviews") or []:
            reviews_by_opp.setdefault(str(review.get("opportunity_id")), []).append(review)
        runner = LLMRunner(max_concurrency=settings.max_llm_concurrency)
        with LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            mock_mode=False,
            cache_enabled=settings.llm_cache_enabled,
        ) as client:
            results = runner.run_many(
                cards,
                lambda card: _judge_with_llm(
                    state,
                    card,
                    reviews_by_opp.get(str(card.get("opportunity_id")), []),
                    client,
                ),
            )
        final = []
        for card, (decision, error) in zip(cards, results):
            if error:
                errors.append(error)
            final.append(
                {
                    **decision,
                    "evidence_ids": card.get("evidence_ids", []),
                    "title": card.get("title"),
                }
            )
        return {**state, "final_decisions": final, "errors": errors}

    cards_by_id = {card["opportunity_id"]: card for card in state.get("validated_cards") or []}
    final = []
    existing_by_id = {
        str(decision.get("opportunity_id")): decision
        for decision in state.get("final_decisions") or []
        if str(decision.get("opportunity_id")) in cards_by_id
    }
    dropped = [
        str(decision.get("opportunity_id"))
        for decision in state.get("final_decisions") or []
        if str(decision.get("opportunity_id")) not in cards_by_id
    ]
    if dropped:
        errors.append(f"final_judge dropped decisions for non-validated cards: {', '.join(dropped)}")
    for card in cards:
        raw_decision = existing_by_id.get(str(card.get("opportunity_id")))
        decision = (
            parse_final_judge_response(raw_decision, card)
            if raw_decision
            else _fallback_decision(card, [], "No prior decision was available.")
        )
        final.append(
            {
                **decision,
                "evidence_ids": card.get("evidence_ids", []),
                "title": card.get("title"),
            }
        )
    return {**state, "final_decisions": final, "errors": errors}
