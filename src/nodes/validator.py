"""Evidence and sustainability check (LLM reasoning).

Unified contract:
- Input preferred: `opportunity_cards: List[dict]` (from reporter/cards)
- Output: `validated_cards`, `rejected_cards` (each card has validation: {passed, reason}),
  `validation_summary`, `is_validated`, `needs_retry` for graph control.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.utils.schema import OpportunityCluster
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SEC = 2.0
QUALITY_THRESHOLD = 0.4  # needs_retry if quality_score < this or passed == 0


class ValidationResult(BaseModel):
    """Per-opportunity: pass/reject and reason."""

    passed: bool = Field(..., description="True if evidence is sufficient and demand is sustained")
    reason: str = Field(..., description="One-sentence reason")


class ValidationList(BaseModel):
    """LLM structured output: one result per opportunity in order."""

    items: list[ValidationResult] = Field(default_factory=list)


def _load_prompt() -> str:
    try:
        import yaml
        p = Path(__file__).resolve().parent.parent / "prompts" / "validator.yaml"
        if p.exists():
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            return (data.get("prompt") or data.get("default") or "").strip()
        return "Decide whether this opportunity has sufficient evidence and sustained demand. Output: pass/fail and a one-sentence reason."
    except Exception as e:
        logger.warning("Load validator prompt failed: %s", e)
        return "Decide whether this opportunity has sufficient evidence and sustained demand. Output: pass/fail and a one-sentence reason."


def _count_evidence_cards(cards: list[dict]) -> int:
    """Total evidence snippet count across cards (for Evidence Saturation gate)."""
    n = 0
    for c in cards:
        for ev in (c.get("evidence") or []):
            if isinstance(ev, str) and ev.strip():
                n += 1
    return n


VALIDATION_SYSTEM = """You are an opportunity validator. For each opportunity (theme + pain points + evidence), decide:
1) Is the evidence sufficient and traceable?
2) Is the demand sustained (not one-off)?
Output exactly one result per opportunity: passed (bool) and reason (one sentence). Keep the same order as the input list."""


def validate(state: dict[str, Any]) -> dict[str, Any]:
    """Validate opportunity cards (preferred) or clusters (compat)."""
    cards: list[dict] = state.get("opportunity_cards") or []
    opportunities: list[OpportunityCluster] = state.get("opportunities") or []
    opportunity_clusters: list[OpportunityCluster] = state.get("opportunity_clusters") or []

    # Preferred path: cards -> validated_cards with validation reason on each card
    if cards:
        use_rule_only = state.get("_validator_rule_only") is True
        if use_rule_only:
            validated_cards = []
            rejected_cards = []
            for c in cards:
                if not isinstance(c, dict):
                    continue
                copy = dict(c)
                theme_ok = str(copy.get("theme") or "").strip()
                copy["validation"] = {"passed": bool(theme_ok), "reason": "rule_fallback"}
                if theme_ok:
                    validated_cards.append(copy)
                else:
                    rejected_cards.append(copy)
            total, passed = len(cards), len(validated_cards)
            quality = passed / max(1, total)
            needs_retry = (passed == 0) or (quality < QUALITY_THRESHOLD)
            current_evidence_count = _count_evidence_cards(validated_cards + rejected_cards)
            return {
                **state,
                "validated_cards": validated_cards,
                "rejected_cards": rejected_cards,
                "validated_opportunities": [],
                "validation_summary": {"total": total, "passed": passed, "quality_score": round(quality, 3)},
                "is_validated": not needs_retry,
                "needs_retry": needs_retry,
                "current_evidence_count": current_evidence_count,
            }

        prompt_extra = _load_prompt()
        body = []
        for i, c in enumerate(cards):
            theme = c.get("theme") or c.get("title") or f"Opportunity {i+1}"
            sample_size = c.get("sample_size")
            confidence = c.get("confidence")
            evidence = c.get("evidence") or []
            pain_points = c.get("pain_points") or []

            part = [
                f"[{i+1}] Theme: {theme}",
                f"Sample size: {sample_size}, confidence: {confidence}",
            ]
            for p in pain_points[:3]:
                if isinstance(p, dict):
                    part.append(f"  - {p.get('complaint')}: {p.get('cause')}")
            for ev in evidence[:6]:
                if isinstance(ev, str) and ev.strip():
                    s = ev.strip()
                    part.append(f"    Evidence: {s[:160]}{'...' if len(s) > 160 else ''}")
            body.append("\n".join(part))

        user_content = (
            prompt_extra
            + "\n\n"
            + "\n\n---\n\n".join(body)
            + "\n\nOutput one ValidationResult (passed, reason) per block above, in the same order."
        )

        llm_factory = state.get("_llm_factory")
        llm = llm_factory() if llm_factory else ChatOpenAI(model="gpt-4o", temperature=0)
        messages = [
            SystemMessage(content=VALIDATION_SYSTEM),
            HumanMessage(content=user_content),
        ]

        result = None
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                structured = llm.with_structured_output(ValidationList)
                result = structured.invoke(messages)
                if len(result.items) >= len(cards):
                    break
                logger.warning(
                    "Validator(cards): LLM result length mismatch (attempt %d), fallback rule",
                    attempt + 1,
                )
                result = None
            except Exception as e:
                last_error = e
                logger.warning("Validator(cards) LLM failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e)
            if result is None and attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SEC)

        if result is not None and len(result.items) >= len(cards):
            all_cards_with_validation = []
            for card, vr in zip(cards, result.items):
                c = dict(card)
                c["validation"] = {"passed": vr.passed, "reason": vr.reason or ""}
                all_cards_with_validation.append(c)
            validated_cards = [c for c in all_cards_with_validation if c["validation"]["passed"]]
            rejected_cards = [c for c in all_cards_with_validation if not c["validation"]["passed"]]
        else:
            # Mismatch or all retries failed: fallback rule, do not treat all as passed
            logger.warning(
                "Validator(cards): using rule fallback (mismatch or LLM failed). Last error: %s",
                last_error,
            )
            validated_cards = []
            rejected_cards = []
            for c in cards:
                if not isinstance(c, dict):
                    continue
                copy = dict(c)
                theme_ok = str(copy.get("theme") or "").strip()
                copy["validation"] = {
                    "passed": bool(theme_ok),
                    "reason": "rule_fallback (LLM unavailable or length mismatch)",
                }
                if theme_ok:
                    validated_cards.append(copy)
                else:
                    rejected_cards.append(copy)

        total = len(cards)
        passed = len(validated_cards)
        quality = passed / max(1, total)
        needs_retry = (passed == 0) or (quality < QUALITY_THRESHOLD)
        current_evidence_count = _count_evidence_cards(validated_cards + rejected_cards)

        logger.info(
            "Validator(cards): in=%d, passed=%d, rejected=%d, quality=%.3f, needs_retry=%s",
            total, passed, len(rejected_cards), quality, needs_retry,
        )
        return {
            **state,
            "validated_cards": validated_cards,
            "rejected_cards": rejected_cards,
            "validated_opportunities": [],
            "validation_summary": {"total": total, "passed": passed, "quality_score": round(quality, 3)},
            "is_validated": not needs_retry,
            "needs_retry": needs_retry,
            "current_evidence_count": current_evidence_count,
        }

    # Compat path: clusters -> validated_opportunities (previous behavior)
    opportunities = opportunity_clusters or opportunities
    if not opportunities:
        return {
            **state,
            "validated_opportunities": [],
            "validated_cards": [],
            "validation_summary": {"total": 0, "passed": 0, "quality_score": 0.0},
            "is_validated": True,
            "needs_retry": False,
        }

    use_rule_only = state.get("_validator_rule_only") is True
    if use_rule_only:
        validated = [o for o in opportunities if o.sample_size >= 0 and o.confidence >= 0]
        total, passed = len(opportunities), len(validated)
        quality = passed / max(1, total)
        needs_retry = (passed == 0) or (quality < QUALITY_THRESHOLD)
        current_evidence_count = sum(len(getattr(p, "evidence", None) or []) for o in opportunities for p in (o.pain_points or []))
        logger.info("Validator (rule): in=%d, out=%d", len(opportunities), len(validated))
        return {
            **state,
            "validated_opportunities": validated,
            "validated_cards": [],
            "validation_summary": {"total": total, "passed": passed, "quality_score": round(quality, 3)},
            "is_validated": not needs_retry,
            "needs_retry": needs_retry,
            "current_evidence_count": current_evidence_count,
        }

    prompt_extra = _load_prompt()
    body = []
    for i, o in enumerate(opportunities):
        part = [f"[{i+1}] Theme: {o.theme}", f"Sample size: {o.sample_size}, confidence: {o.confidence}"]
        for p in o.pain_points[:3]:
            part.append(f"  - {p.complaint}: {p.cause}")
            for ev in (p.evidence or [])[:2]:
                part.append(f"    Evidence: {ev[:120]}{'...' if len(ev) > 120 else ''}")
        body.append("\n".join(part))
    user_content = prompt_extra + "\n\n" + "\n\n---\n\n".join(body) + "\n\nOutput one ValidationResult (passed, reason) per block above, in the same order."

    llm_factory = state.get("_llm_factory")
    llm = llm_factory() if llm_factory else ChatOpenAI(model="gpt-4o", temperature=0)
    messages = [
        SystemMessage(content=VALIDATION_SYSTEM),
        HumanMessage(content=user_content),
    ]

    result = None
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            structured = llm.with_structured_output(ValidationList)
            result = structured.invoke(messages)
            if len(result.items) >= len(opportunities):
                break
            logger.warning("Validator(clusters): LLM result length mismatch (attempt %d), fallback rule", attempt + 1)
            result = None
        except Exception as e:
            last_err = e
            logger.warning("Validator(clusters) LLM failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e)
        if result is None and attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY_SEC)

    if result is not None and len(result.items) >= len(opportunities):
        validated = [opp for opp, vr in zip(opportunities, result.items) if vr.passed]
    else:
        logger.warning("Validator(clusters): rule fallback (mismatch or LLM failed). Last error: %s", last_err)
        validated = [o for o in opportunities if o.sample_size >= 0 and o.confidence >= 0]

    total = len(opportunities)
    passed = len(validated)
    quality = passed / max(1, total)
    needs_retry = (passed == 0) or (quality < QUALITY_THRESHOLD)
    current_evidence_count = sum(len(getattr(p, "evidence", None) or []) for o in opportunities for p in (o.pain_points or []))
    logger.info("Validator(clusters): in=%d, out=%d, quality=%.3f, needs_retry=%s", total, passed, quality, needs_retry)
    return {
        **state,
        "validated_opportunities": validated,
        "validated_cards": [],
        "validation_summary": {"total": total, "passed": passed, "quality_score": round(quality, 3)},
        "is_validated": not needs_retry,
        "needs_retry": needs_retry,
        "current_evidence_count": current_evidence_count,
    }
