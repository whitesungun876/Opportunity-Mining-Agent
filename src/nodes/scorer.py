"""Opportunity scoring (LLM for business dimensions).

Unified contract:
- Preferred input: `validated_cards: List[dict]` (or `opportunity_cards`)
- Compat input: `validated_opportunities: List[OpportunityCluster]`
- Output: `score_cards: List[ScoreCard]`

Optional: set ORACLE_USE_DEBATE=1 or state["_use_debate"]=True to run Hype vs Realist
debate before scoring; Moderator synthesizes the debate into ScoreCards.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.utils.schema import OpportunityCluster, ScoreCard
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SEC = 2.0

SCORER_SYSTEM = """You are a startup strategist. Score each opportunity on five dimensions (0-5 each):
- pain_severity: how severe is the pain
- market_size: potential market size
- willingness_to_pay: how much users would pay
- competition_level: existing competition (lower = less crowded)
- feasibility: how feasible to execute
Output one ScoreCard per opportunity with these five floats (0-5), in the same order as the input list. total_score will be computed automatically."""


class ScoreCardList(BaseModel):
    """One ScoreCard per opportunity, same order."""

    items: list[ScoreCard] = Field(default_factory=list)


def _load_prompt() -> str:
    try:
        import yaml
        p = Path(__file__).resolve().parent.parent / "prompts" / "strategist.yaml"
        if p.exists():
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            return (data.get("prompt") or data.get("default") or "").strip()
        return "Score each opportunity from a strategic angle (market, competition, feasibility, demand sustainability)."
    except Exception as e:
        logger.warning("Load strategist prompt failed: %s", e)
        return "Score each opportunity from a strategic angle (market, competition, feasibility, demand sustainability)."


def score(state: dict[str, Any]) -> dict[str, Any]:
    """Generate ScoreCard list for validated items via LLM (business dimensions)."""
    validated_cards: list[dict] = state.get("validated_cards") or []
    opportunity_cards: list[dict] = state.get("opportunity_cards") or []
    opportunities: list[OpportunityCluster] = state.get("validated_opportunities") or []

    cards_input: list[dict] = validated_cards or opportunity_cards
    if not cards_input and not opportunities:
        return {**state, "score_cards": []}


    prompt_extra = _load_prompt()
    body: list[str] = []
    if cards_input:
        for i, c in enumerate(cards_input):
            theme = c.get("theme") or c.get("title") or f"Opportunity {i+1}"
            sample_size = c.get("sample_size")
            evidence = c.get("evidence") or []
            pains = c.get("pain_points") or []

            part = [f"[{i+1}] {theme}", f"Sample size: {sample_size}"]
            for p in pains[:2]:
                if isinstance(p, dict):
                    part.append(f"  - {p.get('complaint')}: {p.get('cause')}")
            for ev in evidence[:3]:
                if isinstance(ev, str) and ev.strip():
                    s = ev.strip()
                    part.append(f"    Evidence: {s[:140]}{'...' if len(s) > 140 else ''}")
            body.append("\n".join(part))
    else:
        for i, o in enumerate(opportunities):
            part = [f"[{i+1}] {o.theme}", f"Sample size: {o.sample_size}"]
            for p in o.pain_points[:2]:
                part.append(f"  - {p.complaint}: {p.cause}")
            body.append("\n".join(part))

    opportunities_text = "\n\n---\n\n".join(body)
    target_len = len(cards_input) if cards_input else len(opportunities)
    default_card = ScoreCard(
        pain_severity=2.5,
        market_size=2.5,
        willingness_to_pay=2.5,
        competition_level=2.5,
        feasibility=2.5,
    )

    llm_factory = state.get("_llm_factory")
    llm = llm_factory() if llm_factory else ChatOpenAI(model="gpt-4o", temperature=0)
    use_debate = state.get("_use_debate") is True or (os.getenv("ORACLE_USE_DEBATE", "").strip() == "1")

    score_cards: list[ScoreCard] = []
    last_error: Exception | None = None

    if use_debate:
        try:
            from src.agents.debate import run_debate_for_scoring
            score_cards = run_debate_for_scoring(opportunities_text, target_len, llm)
        except Exception as e:
            last_error = e
            logger.warning("Scorer: debate failed, fallback to single-LLM. Error: %s", e)
            use_debate = False

    if not use_debate or not score_cards:
        user_content = (
            prompt_extra
            + "\n\n"
            + opportunities_text
            + "\n\nOutput one ScoreCard per opportunity (pain_severity, market_size, willingness_to_pay, competition_level, feasibility, each 0-5), same order."
        )
        messages = [
            SystemMessage(content=SCORER_SYSTEM),
            HumanMessage(content=user_content),
        ]
        for attempt in range(MAX_RETRIES):
            try:
                structured = llm.with_structured_output(ScoreCardList)
                result = structured.invoke(messages)
                if len(result.items) >= target_len:
                    score_cards = list(result.items[:target_len])
                else:
                    score_cards = [default_card] * target_len
                    logger.warning("Scorer: LLM result length mismatch (attempt %d), using default scores", attempt + 1)
                break
            except Exception as e:
                last_error = e
                logger.warning("Scorer LLM failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY_SEC)
        if not score_cards:
            score_cards = [default_card] * target_len
            logger.warning("Scorer: all retries failed, fallback to rule. Last error: %s", last_error)
    logger.info(
        "Scorer: validated_cards=%d, validated_opportunities=%d, score_cards=%d",
        len(cards_input),
        len(opportunities),
        len(score_cards),
    )
    return {**state, "score_cards": score_cards}