"""Seven-day validation plan generation."""

from __future__ import annotations

from typing import Any

from app.commercial.schemas import ValidationPlan


def _signals_for(opportunity_id: str, wtp_signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in wtp_signals if str(item.get("opportunity_id")) == opportunity_id]


def _recommended_step(card: dict[str, Any], signals: list[dict[str, Any]]) -> str:
    strongest = next((item for item in signals if item.get("strength") == "strong"), None)
    medium = next((item for item in signals if item.get("strength") == "medium"), None)
    if strongest and len(card.get("evidence_ids") or []) >= 5:
        return "validate"
    if medium:
        return "validate"
    if len(card.get("evidence_ids") or []) < 3:
        return "watch"
    return "validate"


def build_validation_plan(card: dict[str, Any], wtp_signals: list[dict[str, Any]]) -> dict[str, Any]:
    opportunity_id = str(card.get("opportunity_id"))
    title = str(card.get("title") or "this opportunity")
    signals = _signals_for(opportunity_id, wtp_signals)
    next_step = _recommended_step(card, signals)
    return ValidationPlan(
        opportunity_id=opportunity_id,
        goal=f"Validate whether the pain behind '{title}' is urgent enough for a paid product hypothesis.",
        seven_day_plan=[
            "Day 1: Contact 10 linked GitHub issue authors or participants with the exact pain statement.",
            "Day 2: Ask how they solve this workflow today, what breaks, and who owns the budget.",
            "Day 3: Build a clickable mockup or workflow demo focused on the top pain.",
            "Day 4: Offer 3 free workflow audits using their current setup or logs.",
            "Day 5: Collect replies, objections, current alternatives, and willingness-to-try signals.",
            "Day 6: Score urgency, budget owner clarity, and willingness to connect data or install a plugin.",
            "Day 7: Decide build, validate, watch, or reject based on replies and prototype pull.",
        ],
        success_criteria=[
            "At least 5 qualified replies from source-linked users or adjacent buyers.",
            "At least 3 users agree to share workflow details, logs, or a demo session.",
            "At least 2 users identify an economic buyer or budget source.",
        ],
        failure_criteria=[
            "Most replies describe a one-off support issue rather than repeated workflow pain.",
            "Users already have a satisfactory alternative and no switching trigger.",
            "No clear buyer, budget source, or urgent validation path emerges.",
        ],
        recommended_next_step=next_step,  # type: ignore[arg-type]
    ).model_dump()


def build_validation_plans(cards: list[dict[str, Any]], wtp_signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [build_validation_plan(card, wtp_signals) for card in cards]
