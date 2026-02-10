"""Memory node: persist validate and score results per opportunity theme to SQLite."""

from __future__ import annotations

from typing import Any

from src.memory.opportunity_store import ensure_table, get_connection, theme_exists, upsert
from src.utils.logger import get_logger
from src.utils.schema import ScoreCard

logger = get_logger(__name__)


def _theme_from_card(card: dict) -> str:
    return (card.get("theme") or card.get("title") or "").strip() or "unknown"


def _theme_from_cluster(cluster: Any) -> str:
    return getattr(cluster, "theme", None) or "unknown"


def memory(state: dict[str, Any]) -> dict[str, Any]:
    """
    Store one record per opportunity theme: insert on first occurrence, update if exists.
    Aligns validated_cards + score_cards (or validated_opportunities + score_cards) by index.
    """
    run_topic = (state.get("topic") or "").strip() or None
    validated_cards: list[dict] = state.get("validated_cards") or []
    score_cards: list[ScoreCard] = state.get("score_cards") or []
    validated_opportunities: list[Any] = state.get("validated_opportunities") or []

    # Prefer cards (per-item validation); else validated_opportunities (batch pass only)
    if validated_cards and len(score_cards) >= len(validated_cards):
        themes_and_validation = [
            (
                _theme_from_card(c),
                c.get("validation") or {},
            )
            for c in validated_cards
        ]
    elif validated_opportunities and len(score_cards) >= len(validated_opportunities):
        themes_and_validation = [
            (_theme_from_cluster(o), {"passed": True, "reason": ""})
            for o in validated_opportunities
        ]
    else:
        logger.warning(
            "Memory: no validated_cards/validated_opportunities or length mismatch with score_cards, skip persist"
        )
        return state

    try:
        with get_connection() as conn:
            ensure_table(conn)
            themes_list = [t for t, _ in themes_and_validation if t and t != "unknown"]
            num_existing = sum(1 for t in themes_list if theme_exists(t, conn))
            low_novelty_ratio = num_existing / max(len(themes_list), 1) if themes_list else 0.0
            state = {**state, "low_novelty_ratio": low_novelty_ratio}
            for i, (theme, val) in enumerate(themes_and_validation):
                if i >= len(score_cards):
                    break
                if not theme or theme == "unknown":
                    continue
                sc = score_cards[i]
                passed = val.get("passed", False) if isinstance(val, dict) else False
                reason = (val.get("reason") or "") if isinstance(val, dict) else ""
                upsert(
                    theme,
                    run_topic=run_topic,
                    validation_passed=passed,
                    validation_reason=reason,
                    pain_severity=getattr(sc, "pain_severity", None),
                    market_size=getattr(sc, "market_size", None),
                    willingness_to_pay=getattr(sc, "willingness_to_pay", None),
                    competition_level=getattr(sc, "competition_level", None),
                    feasibility=getattr(sc, "feasibility", None),
                    total_score=getattr(sc, "total_score", None),
                    conn=conn,
                )
        logger.info("Memory: upserted %d opportunity themes, low_novelty_ratio=%.2f", len(themes_and_validation), low_novelty_ratio)
    except Exception as e:
        logger.warning("Memory: persist failed: %s", e)

    return state
