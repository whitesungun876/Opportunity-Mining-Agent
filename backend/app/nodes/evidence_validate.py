"""Evidence validation node with mock and deterministic real validation."""

from __future__ import annotations

from app.config import get_settings
from app.context.builders import build_context_packet
from app.graph.state import GraphState


HYPOTHESIS_WORDS = {"hypothesis", "assume", "assumption", "estimated", "estimate", "could", "may", "likely", "proposed"}
VALIDATION_MODES = {"strict", "smoke"}


def _evidence_lookup(state: GraphState) -> dict[str, dict]:
    return {str(item.get("evidence_id")): item for item in state.get("evidence_items") or []}


def _pricing_is_hypothesis(card: dict) -> bool:
    pricing = str(card.get("pricing_hypothesis") or "").strip().lower()
    if not pricing:
        return True
    return any(word in pricing for word in HYPOTHESIS_WORDS)


def _normalize_validation_mode(validation_mode: str | None) -> str:
    mode = (validation_mode or "strict").strip().lower()
    if mode not in VALIDATION_MODES:
        return "strict"
    return mode


def _minimum_evidence_count(validation_mode: str) -> int:
    return 1 if validation_mode == "smoke" else 3


def validate_card_deterministic(
    card: dict,
    evidence_by_id: dict[str, dict],
    *,
    validation_mode: str = "strict",
) -> dict:
    """Validate one opportunity card against evidence presence and claim rules."""
    mode = _normalize_validation_mode(validation_mode)
    min_evidence_count = _minimum_evidence_count(mode)
    evidence_ids = [str(item) for item in card.get("evidence_ids", [])]
    valid_evidence_ids = [
        evidence_id
        for evidence_id in dict.fromkeys(evidence_ids)
        if evidence_id in evidence_by_id and evidence_by_id[evidence_id].get("source_url")
    ]
    evidence_urls = [evidence_by_id[evidence_id]["source_url"] for evidence_id in valid_evidence_ids]
    evidence_count = len(valid_evidence_ids)
    missing_evidence_claims: list[str] = []
    unsupported_claims: list[str] = []
    weak_claims: list[str] = []

    if evidence_count < min_evidence_count:
        missing_evidence_claims.append(
            f"{mode} validation requires at least {min_evidence_count} valid evidence_id(s)."
        )
    is_weak_card = bool(card.get("weak_card") or evidence_count < 3)
    if is_weak_card:
        weak_claims.append("Card is marked weak_card because it has fewer than 3 evidence_ids.")
    if not _pricing_is_hypothesis(card):
        unsupported_claims.append("pricing_hypothesis must be phrased as a hypothesis, assumption, or estimate.")
    combined_claim_text = " ".join(
        str(card.get(key, ""))
        for key in ["pain_summary", "commercial_gap", "pricing_hypothesis", "target_user"]
    ).lower()
    if any(term in combined_claim_text for term in ["billion", "tam", "market size", "huge market"]) and "hypothesis" not in combined_claim_text:
        unsupported_claims.append("Market-size claim lacks evidence and must be framed as a hypothesis.")

    grounding_rate = evidence_count / max(1, len(evidence_ids))
    is_valid = evidence_count >= min_evidence_count and not unsupported_claims
    rejection_reasons = missing_evidence_claims + unsupported_claims
    revision = ""
    if not is_valid:
        revision = "Add more valid GitHub evidence and rewrite unsupported factual claims as hypotheses."
    return {
        **card,
        "evidence_ids": valid_evidence_ids,
        "evidence_urls": evidence_urls,
        "weak_card": is_weak_card,
        "validation": {
            "opportunity_id": card.get("opportunity_id"),
            "is_valid": is_valid,
            "passed": is_valid,
            "validation_mode": mode,
            "validation_status": "validated" if is_valid else "rejected",
            "evidence_count": evidence_count,
            "evidence_urls_count": len(evidence_urls),
            "grounding_rate": round(grounding_rate, 3),
            "missing_evidence_claims": missing_evidence_claims,
            "unsupported_claims": unsupported_claims,
            "weak_claims": weak_claims,
            "rejection_reasons": rejection_reasons,
            "valid_evidence_ids": valid_evidence_ids,
            "revision_suggestion": revision,
        },
    }


def evidence_validate(state: GraphState) -> GraphState:
    settings = get_settings()
    if not settings.mock_mode:
        cards = state.get("opportunity_cards") or []
        evidence_by_id = _evidence_lookup(state)
        validation_mode = _normalize_validation_mode(settings.validation_mode)
        packet = build_context_packet(
            node_name="evidence_validate",
            goal="Validate opportunity cards against known GitHub evidence ids and URLs.",
            input_items=[
                {
                    "opportunity_id": card.get("opportunity_id"),
                    "evidence_ids": card.get("evidence_ids", []),
                    "pricing_hypothesis": card.get("pricing_hypothesis"),
                    "weak_card": card.get("weak_card", False),
                }
                for card in cards
            ],
            evidence_ids=[evidence_id for card in cards for evidence_id in card.get("evidence_ids", [])],
            output_schema={
                "validated_cards": "list[dict]",
                "rejected_cards": "list[dict]",
            },
            prompt_version="evidence_validator:deterministic-v1",
        )
        _ = packet
        checked = [
            validate_card_deterministic(card, evidence_by_id, validation_mode=validation_mode)
            for card in cards
        ]
        validated = [card for card in checked if (card.get("validation") or {}).get("is_valid")]
        rejected = [card for card in checked if not (card.get("validation") or {}).get("is_valid")]
        return {**state, "validated_cards": validated, "rejected_cards": rejected}

    issue_by_id = {issue["issue_id"]: issue for issue in state.get("high_value_issues") or []}
    validated = []
    for card in state.get("opportunity_cards") or []:
        evidence_urls = [
            issue_by_id[eid].get("url") or issue_by_id[eid].get("source_url")
            for eid in card.get("evidence_ids", [])
            if eid in issue_by_id and "github.com" in (issue_by_id[eid].get("url") or issue_by_id[eid].get("source_url") or "")
        ]
        passed = len(evidence_urls) >= 3
        rejection_reasons = [] if passed else ["mock validation requires at least 3 GitHub evidence URLs."]
        validated.append(
            {
                **card,
                "evidence_urls": evidence_urls,
                "weak_card": bool(card.get("weak_card", False) or len(evidence_urls) < 3),
                "validation": {
                    "opportunity_id": card.get("opportunity_id"),
                    "is_valid": passed,
                    "passed": passed,
                    "validation_mode": "strict",
                    "validation_status": "validated" if passed else "rejected",
                    "evidence_count": len(evidence_urls),
                    "evidence_urls_count": len(evidence_urls),
                    "rejection_reasons": rejection_reasons,
                    "reason": "at least 3 mock GitHub issue evidence URLs" if passed else "insufficient evidence",
                },
            }
        )
    return {**state, "validated_cards": validated}
