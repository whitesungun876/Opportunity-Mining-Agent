"""Opportunity card deduplication node."""

from __future__ import annotations

import re
from typing import Any

from app.graph.state import GraphState


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9_+-]*", text.lower()))


def _card_text(card: dict[str, Any]) -> str:
    return " ".join(
        str(card.get(key) or "")
        for key in ["title", "pain_summary", "commercial_gap", "problem"]
    )


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / max(1, len(left | right))


def _score(card: dict[str, Any]) -> float:
    score_json = card.get("score_json") if isinstance(card.get("score_json"), dict) else {}
    try:
        base = float(score_json.get("overall", 0))
    except (TypeError, ValueError):
        base = 0.0
    return base + len(card.get("evidence_ids") or []) * 3


def _is_duplicate(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_evidence = set(str(item) for item in left.get("evidence_ids", []) if str(item).strip())
    right_evidence = set(str(item) for item in right.get("evidence_ids", []) if str(item).strip())
    evidence_overlap = len(left_evidence & right_evidence) / max(1, min(len(left_evidence), len(right_evidence)))
    if evidence_overlap >= 0.6:
        return True
    return _jaccard(_tokens(_card_text(left)), _tokens(_card_text(right))) >= 0.55


def _merge_cards(base: dict[str, Any], duplicate: dict[str, Any]) -> dict[str, Any]:
    primary, secondary = (base, duplicate) if _score(base) >= _score(duplicate) else (duplicate, base)
    merged_from = list(dict.fromkeys(
        (primary.get("merged_from") or [primary.get("opportunity_id")])
        + (secondary.get("merged_from") or [secondary.get("opportunity_id")])
    ))
    evidence_ids = list(dict.fromkeys((primary.get("evidence_ids") or []) + (secondary.get("evidence_ids") or [])))
    evidence_urls = list(dict.fromkeys((primary.get("evidence_urls") or []) + (secondary.get("evidence_urls") or [])))
    source_repos = list(dict.fromkeys((primary.get("source_repos") or []) + (secondary.get("source_repos") or [])))
    return {
        **primary,
        "evidence_ids": evidence_ids,
        "evidence_urls": evidence_urls,
        "source_repos": source_repos,
        "merged_from": merged_from,
        "weak_card": bool(primary.get("weak_card") and len(evidence_ids) < 3),
    }


def dedupe_opportunities(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    for card in cards:
        merged = False
        for idx, existing in enumerate(deduped):
            if _is_duplicate(existing, card):
                deduped[idx] = _merge_cards(existing, card)
                merged = True
                break
        if not merged:
            deduped.append({**card, "merged_from": card.get("merged_from") or [card.get("opportunity_id")]})
    return deduped


def opportunity_dedup(state: GraphState) -> GraphState:
    cards = state.get("opportunity_cards") or []
    deduped = dedupe_opportunities(cards)
    return {**state, "opportunity_cards": deduped}
