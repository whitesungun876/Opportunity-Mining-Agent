"""Report writer node."""

from __future__ import annotations

from app.config import get_settings
from app.graph.state import GraphState


def _evidence_lookup(state: GraphState) -> dict[str, dict]:
    return {str(item.get("evidence_id")): item for item in state.get("evidence_items") or []}


def _reviews_by_opp(state: GraphState) -> dict[str, list[dict]]:
    valid_ids = {str(card.get("opportunity_id")) for card in state.get("validated_cards") or []}
    out: dict[str, list[dict]] = {}
    for review in state.get("agent_reviews") or []:
        opportunity_id = str(review.get("opportunity_id"))
        if opportunity_id in valid_ids:
            out.setdefault(opportunity_id, []).append(review)
    return out


def _decisions_by_opp(state: GraphState) -> dict[str, dict]:
    valid_ids = {str(card.get("opportunity_id")) for card in state.get("validated_cards") or []}
    return {
        str(item.get("opportunity_id")): item
        for item in state.get("final_decisions") or []
        if str(item.get("opportunity_id")) in valid_ids
    }


def _items_by_opp(items: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for item in items:
        opportunity_id = str(item.get("opportunity_id"))
        if opportunity_id:
            out.setdefault(opportunity_id, []).append(item)
    return out


def _one_by_opp(items: list[dict]) -> dict[str, dict]:
    return {str(item.get("opportunity_id")): item for item in items if item.get("opportunity_id")}


def _append_performance_summary(lines: list[str], state: GraphState) -> None:
    timings = state.get("node_latency_summary") or []
    if not timings:
        return
    slowest = sorted(timings, key=lambda item: float(item.get("latency_ms") or 0), reverse=True)[:5]
    lines.extend(["", "## Performance Summary", ""])
    lines.append("Node latency is recorded to help compare quick, standard, and deep runs.")
    for item in slowest:
        node = str(item.get("node_name") or "unknown").replace("_", " ")
        latency = float(item.get("latency_ms") or 0)
        lines.append(f"- {node}: {latency / 1000:.2f}s")


def _append_signal_diagnostics(lines: list[str], state: GraphState) -> None:
    diagnostics = state.get("signal_diagnostics") or {}
    if not diagnostics:
        return
    stage = str(diagnostics.get("low_signal_stage") or "unknown")
    if stage == "unknown" and diagnostics.get("validated_cards_count"):
        return
    lines.extend(["", "## Low Signal Diagnostics", ""])
    lines.append(f"- Low-signal type: {diagnostics.get('low_signal_type', 'unknown')}")
    lines.append(f"- Low-signal stage: {stage}")
    lines.append(f"- Reason: {diagnostics.get('low_signal_reason', '')}")
    lines.append(f"- Raw issues: {diagnostics.get('raw_issues_count', 0)}")
    lines.append(f"- Evidence items: {diagnostics.get('evidence_items_count', 0)}")
    lines.append(f"- High-value issues: {diagnostics.get('high_value_issues_count', 0)}")
    lines.append(f"- Pain clusters: {diagnostics.get('pain_clusters_count', 0)}")
    lines.append(f"- Filtered pain clusters: {diagnostics.get('filtered_pain_clusters_count', 0)}")
    lines.append(f"- Opportunity hypotheses: {diagnostics.get('opportunity_cards_count', 0)}")
    lines.append(f"- Validated cards: {diagnostics.get('validated_cards_count', 0)}")
    actions = diagnostics.get("suggested_recovery_actions") or []
    if actions:
        lines.append("- Suggested recovery actions: " + ", ".join(actions))


def _render_real_report(state: GraphState) -> str:
    cards = state.get("validated_cards") or []
    evidence_by_id = _evidence_lookup(state)
    reviews_by_opp = _reviews_by_opp(state)
    decisions_by_opp = _decisions_by_opp(state)
    buyers_by_opp = _one_by_opp(state.get("buyer_hypotheses") or [])
    wtp_by_opp = _items_by_opp(state.get("wtp_signals") or [])
    alternatives_by_opp = _items_by_opp(state.get("competitor_alternatives") or [])
    outreach_by_opp = _items_by_opp(state.get("outreach_targets") or [])
    plans_by_opp = _one_by_opp(state.get("validation_plans") or [])
    errors = state.get("errors") or []

    lines = [
        "# GitHub Opportunity Miner Report",
        "",
        "This report is rendered from validated cards, commercial validation outputs, final decisions, agent reviews, evidence items, and errors only.",
        "",
        "GitHub evidence proves pain, not payment. Buyer and willingness-to-pay sections are hypotheses until validated with real users.",
        "",
        "## Run Summary",
        "",
        f"- Evidence items: {len(state.get('evidence_items') or [])}",
        f"- Validated opportunities: {len(cards)}",
        f"- Final decisions: {len(decisions_by_opp)}",
        f"- Agent reviews: {sum(len(items) for items in reviews_by_opp.values())}",
        f"- Errors: {len(errors)}",
        "",
        "## Opportunity Cards",
    ]

    if not cards:
        lines.append("")
        lines.append("No validated opportunity cards.")

    for card in cards:
        opportunity_id = str(card.get("opportunity_id"))
        decision = decisions_by_opp.get(opportunity_id, {})
        reviews = reviews_by_opp.get(opportunity_id, [])
        buyer = buyers_by_opp.get(opportunity_id, {})
        wtp_signals = wtp_by_opp.get(opportunity_id, [])
        strongest_wtp = sorted(
            wtp_signals,
            key=lambda item: {"strong": 3, "medium": 2, "weak": 1}.get(str(item.get("strength")), 0),
            reverse=True,
        )
        wtp = strongest_wtp[0] if strongest_wtp else {}
        alternatives = alternatives_by_opp.get(opportunity_id, [])
        outreach = outreach_by_opp.get(opportunity_id, [])
        plan = plans_by_opp.get(opportunity_id, {})
        lines.extend(
            [
                "",
                f"### {card.get('title', opportunity_id)}",
                "",
                f"- Opportunity ID: `{opportunity_id}`",
                f"- Decision: {decision.get('decision', 'watch')}",
                f"- Score: {decision.get('score', 0)}",
                f"- Product form: {decision.get('best_product_form') or card.get('best_product_form') or card.get('product_form')}",
                f"- Migration cost: {decision.get('migration_cost') or card.get('migration_cost')}",
                f"- Target user: {card.get('target_user', '')}",
                f"- Pain summary: {card.get('pain_summary') or card.get('problem') or ''}",
                f"- Commercial gap: {card.get('commercial_gap') or card.get('problem') or ''}",
                f"- Pricing hypothesis: {card.get('pricing_hypothesis', '')}",
                "",
                "#### Buyer Hypothesis",
                f"- End user: {buyer.get('end_user', 'Hypothesis: unknown end user')}",
                f"- Economic buyer: {buyer.get('economic_buyer', 'Hypothesis: unknown economic buyer')}",
                f"- Budget source: {buyer.get('budget_source', 'Hypothesis: unknown budget source')}",
                f"- Buying trigger: {buyer.get('buying_trigger', 'Hypothesis: needs validation')}",
                "",
                "#### Willingness-to-Pay Signal",
                f"- Strength: {wtp.get('strength', 'weak')}",
                f"- Signal: {wtp.get('signal_summary', 'Payment hypothesis remains weak until validated.')}",
                f"- Reason: {wtp.get('reason', 'No explicit payment signal found.')}",
                "",
                "#### Current Alternatives",
            ]
        )
        for alternative in alternatives[:3]:
            lines.append(
                f"- {alternative.get('name')}: {alternative.get('limitation')} "
                f"(confidence={alternative.get('confidence')}, source={alternative.get('source') or 'low-confidence hypothesis'})"
            )

        lines.extend(
            [
                "",
                "#### First Users to Contact",
            ]
        )
        for target in outreach[:5]:
            user = target.get("github_user") or "GitHub participant"
            lines.append(f"- {user} via [{target.get('source_repo')}]({target.get('source_url')}): {target.get('outreach_angle')}")

        lines.extend(
            [
                "",
                "#### 7-Day Validation Plan",
            ]
        )
        for step in (plan.get("seven_day_plan") or [])[:7]:
            lines.append(f"- {step}")
        lines.extend(
            [
                "",
                "#### Validation Actions",
            ]
        )
        for action in card.get("validation_actions") or [decision.get("first_validation_action", "")]:
            if action:
                lines.append(f"- {action}")
        if decision.get("first_validation_action"):
            lines.append(f"- First judge action: {decision['first_validation_action']}")

        lines.extend(["", "#### Risks"])
        for risk in (card.get("risks") or [])[:5]:
            lines.append(f"- {risk}")
        for risk in (decision.get("top_risks") or [])[:5]:
            lines.append(f"- Judge risk: {risk}")

        lines.extend(["", "#### Agent Reviews"])
        for review in reviews:
            lines.append(
                f"- {review.get('agent')}: score={review.get('score')}, "
                f"recommendation={review.get('recommendation')}; "
                f"{review.get('key_argument', '')} Risk: {review.get('main_risk', '')}"
            )

        lines.extend(["", "#### Evidence"])
        for evidence_id in card.get("evidence_ids", [])[:10]:
            evidence = evidence_by_id.get(str(evidence_id), {})
            source_url = evidence.get("source_url")
            title = evidence.get("title", "")
            if source_url:
                lines.append(f"- `{evidence_id}` [{title}]({source_url})")
            else:
                lines.append(f"- `{evidence_id}` missing source_url")

    if errors:
        lines.extend(["", "## Errors Summary"])
        for err in errors[:20]:
            lines.append(f"- {err}")

    _append_signal_diagnostics(lines, state)
    _append_performance_summary(lines, state)

    fusion_candidates = state.get("validated_fusion_candidates") or []
    if fusion_candidates:
        lines.extend(["", "## Fusion Discovery", ""])
        lines.append("Fusion candidates combine GitHub pain, mature repo capability, and optional research support.")
        for candidate in fusion_candidates[:5]:
            capability = candidate.get("capability") or {}
            papers = candidate.get("research_evidence") or []
            lines.extend(
                [
                    "",
                    f"### {candidate.get('title', candidate.get('fusion_id'))}",
                    "",
                    f"- Fusion thesis: {candidate.get('fusion_thesis', '')}",
                    f"- Source repo capability: {capability.get('name', '')} from `{capability.get('source_repo', '')}`",
                    f"- Overall score: {candidate.get('overall_score', 0)}",
                    f"- Evidence IDs: {', '.join(candidate.get('evidence_ids') or [])}",
                    "- Research support is technical feasibility evidence, not proof of willingness to pay.",
                ]
            )
            for paper in papers[:3]:
                if paper.get("url"):
                    lines.append(f"- Research: [{paper.get('title')}]({paper.get('url')})")

    return "\n".join(lines)


def report_write(state: GraphState) -> GraphState:
    if not get_settings().mock_mode:
        return {**state, "report_markdown": _render_real_report(state)}

    lines = [
        "# GitHub Opportunity Miner Report",
        "",
        f"**Topic:** {state.get('canonical_topic', '')}",
        "",
        "## Opportunity Cards",
    ]
    decisions = {item.get("opportunity_id"): item for item in state.get("final_decisions") or []}
    for card in state.get("validated_cards") or []:
        decision = decisions.get(card["opportunity_id"], {})
        lines.extend(
            [
                "",
                f"### {card['title']}",
                f"- Decision: {decision.get('decision', 'watch')}",
                f"- Score: {decision.get('score', 0)}",
                f"- Migration cost: {card.get('migration_cost')}",
                f"- Product form: {card.get('best_product_form')}",
                "- Evidence:",
            ]
        )
        for url in card.get("evidence_urls", [])[:5]:
            lines.append(f"  - {url}")
    _append_signal_diagnostics(lines, state)
    _append_performance_summary(lines, state)
    return {**state, "report_markdown": "\n".join(lines)}
