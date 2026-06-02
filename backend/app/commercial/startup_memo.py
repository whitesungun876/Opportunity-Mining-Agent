"""Startup memo composition."""

from __future__ import annotations

from typing import Any

from app.commercial.schemas import StartupMemo


def _by_opp(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        out.setdefault(str(item.get("opportunity_id")), []).append(item)
    return out


def _one_by_opp(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("opportunity_id")): item for item in items if item.get("opportunity_id")}


def build_startup_memos(
    cards: list[dict[str, Any]],
    *,
    buyer_hypotheses: list[dict[str, Any]],
    wtp_signals: list[dict[str, Any]],
    alternatives: list[dict[str, Any]],
    outreach_targets: list[dict[str, Any]],
    validation_plans: list[dict[str, Any]],
    final_decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    buyer_by_id = _one_by_opp(buyer_hypotheses)
    signals_by_id = _by_opp(wtp_signals)
    alternatives_by_id = _by_opp(alternatives)
    outreach_by_id = _by_opp(outreach_targets)
    plans_by_id = _one_by_opp(validation_plans)
    decisions_by_id = _one_by_opp(final_decisions)
    memos: list[dict[str, Any]] = []
    for card in cards:
        opportunity_id = str(card.get("opportunity_id"))
        buyer = buyer_by_id.get(opportunity_id, {})
        signals = signals_by_id.get(opportunity_id, [])
        strongest = sorted(signals, key=lambda item: {"strong": 3, "medium": 2, "weak": 1}.get(str(item.get("strength")), 0), reverse=True)
        signal = strongest[0] if strongest else {}
        plan = plans_by_id.get(opportunity_id, {})
        decision = decisions_by_id.get(opportunity_id, {})
        outreach = outreach_by_id.get(opportunity_id, [])
        current_alternatives = [
            f"{item.get('name')}: {item.get('limitation')}"
            for item in alternatives_by_id.get(opportunity_id, [])
        ]
        evidence_count = len(card.get("evidence_ids") or [])
        memo = StartupMemo(
            opportunity_id=opportunity_id,
            title=str(card.get("title") or opportunity_id),
            target_buyer=str(buyer.get("economic_buyer") or "Hypothesis: Head of Engineering or CTO"),
            end_user=str(buyer.get("end_user") or card.get("target_user") or "Hypothesis: engineering teams"),
            pain_summary=str(card.get("pain_summary") or card.get("problem") or ""),
            evidence_summary=f"Evidence-backed pain: {evidence_count} linked GitHub evidence items support this opportunity.",
            commercial_gap=str(card.get("commercial_gap") or card.get("problem") or ""),
            current_alternatives=current_alternatives,
            willingness_to_pay_hypothesis=str(signal.get("signal_summary") or "Payment hypothesis remains weak until validated with source users."),
            mvp=[str(item) for item in card.get("mvp_features") or []][:5],
            pricing_hypothesis=str(card.get("pricing_hypothesis") or "Hypothesis: pricing requires validation interviews."),
            outreach_targets=[
                f"{item.get('github_user') or 'GitHub participant'} via {item.get('source_url')}"
                for item in outreach[:5]
            ],
            validation_plan=[str(item) for item in plan.get("seven_day_plan") or []],
            risks=[str(item) for item in (card.get("risks") or [])[:5]],
            final_decision=str(decision.get("decision") or plan.get("recommended_next_step") or "validate"),  # type: ignore[arg-type]
        )
        memos.append(memo.model_dump())
    return memos
