"""Outreach target extraction from GitHub evidence."""

from __future__ import annotations

from typing import Any

from app.commercial.schemas import OutreachTarget


def _repo_label(item: dict[str, Any]) -> str:
    if item.get("repo_owner") or item.get("repo_name"):
        return f"{item.get('repo_owner', '')}/{item.get('repo_name', '')}".strip("/")
    return str(item.get("repo") or item.get("repo_url") or "unknown/repo")


def _pain_by_evidence(pain_points: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(pain.get("evidence_id")): pain for pain in pain_points if pain.get("evidence_id")}


def build_outreach_targets(
    cards: list[dict[str, Any]],
    evidence_items: list[dict[str, Any]],
    pain_points: list[dict[str, Any]],
    *,
    max_per_card: int = 5,
) -> list[dict[str, Any]]:
    evidence_by_id = {str(item.get("evidence_id")): item for item in evidence_items}
    pain_lookup = _pain_by_evidence(pain_points)
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for card in cards:
        opportunity_id = str(card.get("opportunity_id"))
        count = 0
        for evidence_id in card.get("evidence_ids") or []:
            item = evidence_by_id.get(str(evidence_id))
            if not item or not item.get("source_url"):
                continue
            pain = pain_lookup.get(str(evidence_id), {})
            github_user = item.get("author_login") or None
            key = (opportunity_id, str(item.get("source_url")))
            if key in seen:
                continue
            seen.add(key)
            pain_type = str(pain.get("pain_type") or "production workflow pain")
            out.append(
                OutreachTarget(
                    opportunity_id=opportunity_id,
                    github_user=github_user,
                    source_url=str(item.get("source_url")),
                    source_repo=_repo_label(item),
                    pain_type=pain_type,
                    why_contact=(
                        f"Authored or participated in GitHub evidence about {pain_type}; "
                        "this is a source lead, not assumed buyer identity."
                    ),
                    outreach_angle=(
                        "Ask how they handle this workflow today and whether a lightweight prototype "
                        "would be worth trying. Do not assume willingness to pay."
                    ),
                ).model_dump()
            )
            count += 1
            if count >= max_per_card:
                break
    return out
