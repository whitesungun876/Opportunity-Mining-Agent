"""Final report generation + structured opportunity cards.

This module serves 2 roles:
1) Build `opportunity_cards: List[dict]` for Validator/Scorer consumption.
2) Build `final_report: str | dict` as the end-of-graph output.
"""

from __future__ import annotations

from typing import Any

from src.utils.schema import OpportunityCluster, ScoreCard
from src.utils.logger import get_logger

logger = get_logger(__name__)


def build_opportunity_cards(state: dict[str, Any], *, top_k: int | None = None) -> list[dict]:
    """
    Convert opportunity clusters into structured dict cards for downstream nodes (validator/scorer).
    Deterministic and non-LLM.
    """
    clusters: list[OpportunityCluster] = (
        state.get("opportunity_clusters")
        or state.get("validated_opportunities")
        or state.get("opportunities")
        or []
    )
    if top_k is not None and top_k > 0:
        clusters = clusters[:top_k]

    cards: list[dict] = []
    for idx, c in enumerate(clusters):
        evidence: list[str] = []
        seen = set()
        for p in c.pain_points or []:
            for ev in (p.evidence or [])[:3]:
                ev = (ev or "").strip()
                if not ev or ev in seen:
                    continue
                seen.add(ev)
                evidence.append(ev)
                if len(evidence) >= 8:
                    break
            if len(evidence) >= 8:
                break

        cards.append(
            {
                "id": f"opp_{idx+1}",
                "theme": c.theme,
                "sample_size": int(c.sample_size),
                "confidence": float(c.confidence),
                "pain_points": [
                    {
                        "complaint": p.complaint,
                        "cause": p.cause,
                        "persona": p.persona,
                        "context": p.context,
                        "action_intent": p.action_intent,
                    }
                    for p in (c.pain_points or [])[:6]
                ],
                "evidence": evidence,
            }
        )
    return cards


def cards(state: dict[str, Any]) -> dict[str, Any]:
    """Graph node: build `opportunity_cards` for Validator."""
    top_k = state.get("_cards_top_k")
    try:
        top_k = int(top_k) if top_k is not None else None
    except Exception:
        top_k = None
    cards_out = build_opportunity_cards(state, top_k=top_k)
    logger.info("Reporter(cards): clusters=%d, cards=%d", len(state.get("opportunity_clusters") or []), len(cards_out))
    return {**state, "opportunity_cards": cards_out}


def report(state: dict[str, Any]) -> dict[str, Any]:
    """Format validated_* + score_cards into final report string (graph node)."""
    out = reporter_node(
        state,
        top_k=state.get("_report_top_k"),
    )
    report_md = out.get("report_markdown", "")
    return {
        **state,
        # new contract
        "final_report": report_md,
        # backward compat
        "report": report_md,
        "report_markdown": report_md,
    }


def reporter_node(state: dict[str, Any], *, top_k: int | None = None) -> dict[str, Any]:
    """
    Build markdown report from topic + (validated_opportunities | validated_cards | opportunity_clusters).
    Returns dict with report_markdown. Optional top_k limits number of clusters shown.
    """
    topic = state.get("topic") or "Opportunity Report"
    clusters: list[OpportunityCluster] = (
        state.get("opportunity_clusters")
        or state.get("validated_opportunities")
        or state.get("opportunities")
        or []
    )
    validated_cards: list[dict] = state.get("validated_cards") or []
    score_cards: list[ScoreCard] = state.get("score_cards") or []

    if top_k is not None and top_k > 0:
        clusters = clusters[:top_k]
        validated_cards = validated_cards[:top_k]

    validation_summary = state.get("validation_summary") or {}
    rejected_cards: list[dict] = state.get("rejected_cards") or []

    lines = ["# Startup Oracle Report", ""]
    if topic:
        lines.append(f"**Topic:** {topic}")
        lines.append("")
    if validation_summary:
        total = validation_summary.get("total")
        passed = validation_summary.get("passed")
        quality = validation_summary.get("quality_score")
        if total is not None and passed is not None:
            lines.append("### Validation summary")
            lines.append(f"- Total: {total}, Passed: {passed}, Quality: {quality}")
            lines.append("")
    if rejected_cards:
        lines.append("### Rejected opportunities")
        for c in rejected_cards[:20]:
            theme = c.get("theme") or c.get("title") or "Unknown"
            val = c.get("validation") or {}
            reason = val.get("reason") or "No reason given"
            lines.append(f"- **{theme}** — ❌ {reason}")
        lines.append("")
    if validated_cards:
        lines.append("### Validated opportunities")
        for i, c in enumerate(validated_cards):
            sc = score_cards[i] if i < len(score_cards) else None
            score_val = sc.total_score if sc is not None else None
            theme = c.get("theme") or c.get("title") or f"Opportunity {i+1}"
            sample_size = c.get("sample_size")
            confidence = c.get("confidence")
            evidence = c.get("evidence") or []
            val = c.get("validation") or {}
            reason = val.get("reason") or ""

            lines.append(f"## {theme}")
            if reason:
                lines.append(f"- ✅ Validation: {reason}")
            if score_val is not None:
                lines.append(f"- Total score: {score_val:.1f}")
            if sample_size is not None or confidence is not None:
                ss = sample_size if sample_size is not None else "?"
                cf = float(confidence) if confidence is not None else 0.0
                lines.append(f"- Sample size: {ss}, confidence: {cf:.2f}")
            lines.append("")
            lines.append("### Evidence")
            for ev in evidence[:12]:
                if isinstance(ev, str) and ev.strip():
                    lines.append(f"- {ev.strip()}")
            if sc is not None:
                lines.append("")
                lines.append(
                    f"- Dimensions: pain_severity={sc.pain_severity}, market_size={sc.market_size}, "
                    f"willingness_to_pay={sc.willingness_to_pay}, competition={sc.competition_level}, "
                    f"feasibility={sc.feasibility}"
                )
            lines.append("")
    else:
        for i, c in enumerate(clusters):
            card = score_cards[i] if i < len(score_cards) else None
            score_val = card.total_score if card is not None else None
            lines.append(f"## {c.theme}")
            if score_val is not None:
                lines.append(f"- Total score: {score_val:.1f}")
            lines.append(f"- Sample size: {c.sample_size}, confidence: {c.confidence:.2f}")
            lines.append("")
            lines.append("### Evidence")
            for p in c.pain_points:
                for ev in p.evidence:
                    lines.append(f"- {ev}")
            if card is not None:
                lines.append("")
                lines.append(
                    f"- Dimensions: pain_severity={card.pain_severity}, market_size={card.market_size}, "
                    f"willingness_to_pay={card.willingness_to_pay}, competition={card.competition_level}, "
                    f"feasibility={card.feasibility}"
                )
            lines.append("")

    report_md = "\n".join(lines)
    logger.info("Reporter: report length=%d", len(report_md))
    return {**state, "report_markdown": report_md, "report": report_md, "final_report": report_md}
