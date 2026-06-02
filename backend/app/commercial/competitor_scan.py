"""Lightweight competitor and alternative scan."""

from __future__ import annotations

from typing import Any

from app.commercial.schemas import CompetitorAlternative


KNOWN_ALTERNATIVES = {
    "grafana": ("Grafana", "open_source"),
    "prometheus": ("Prometheus", "open_source"),
    "datadog": ("Datadog", "commercial"),
    "sentry": ("Sentry", "commercial"),
    "langfuse": ("Langfuse", "open_source"),
    "github actions": ("GitHub Actions", "commercial"),
    "jira": ("Jira", "commercial"),
    "spreadsheet": ("Spreadsheet workflow", "manual_process"),
    "manual": ("Manual process", "manual_process"),
    "internal": ("Internal workaround", "internal_workaround"),
    "homegrown": ("Homegrown tool", "internal_workaround"),
}


def _related_evidence(card: dict[str, Any], evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence_ids = {str(item) for item in card.get("evidence_ids") or []}
    return [item for item in evidence_items if str(item.get("evidence_id")) in evidence_ids]


def scan_alternatives_for_card(card: dict[str, Any], evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    related = _related_evidence(card, evidence_items)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in related:
        text = f"{item.get('title', '')} {item.get('body', '')}".lower()
        for needle, (name, alt_type) in KNOWN_ALTERNATIVES.items():
            if needle not in text or name in seen:
                continue
            seen.add(name)
            out.append(
                CompetitorAlternative(
                    opportunity_id=str(card.get("opportunity_id")),
                    name=name,
                    type=alt_type,  # type: ignore[arg-type]
                    how_users_use_it="Hypothesis: mentioned as a tool, workaround, or adjacent workflow in the linked GitHub evidence.",
                    limitation="Hypothesis: the mention does not prove this alternative fully solves the validated production pain.",
                    confidence=0.65,
                    source=item.get("source_url"),
                ).model_dump()
            )
    if not out:
        out.append(
            CompetitorAlternative(
                opportunity_id=str(card.get("opportunity_id")),
                name="Manual or internal workflow",
                type="manual_process",
                how_users_use_it="Hypothesis: teams may rely on internal scripts, manual review, or ad hoc debugging.",
                limitation="Low-confidence fallback because no explicit alternative was found in linked evidence.",
                confidence=0.3,
                source=(related[0].get("source_url") if related else None),
            ).model_dump()
        )
    return out


def scan_alternatives(cards: list[dict[str, Any]], evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for card in cards:
        out.extend(scan_alternatives_for_card(card, evidence_items))
    return out
