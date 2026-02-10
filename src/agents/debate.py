"""Multi-agent debate: Hype vs Realist for balanced scoring.

One agent (Hype) argues for each opportunity; another (Realist) plays investor and
challenges. A Moderator synthesizes the debate into final ScoreCards to reduce bias.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from src.utils.schema import ScoreCard
from src.utils.logger import get_logger

logger = get_logger(__name__)

HYPE_SYSTEM = """You are the "Hype" agent in a startup debate. Your job is to argue why each opportunity is strong.
For each opportunity listed, give 2–3 sentences: emphasize pain severity, market potential, willingness to pay, feasibility, and why competition is manageable. Be persuasive but stay grounded in the evidence given. Keep the same order as the input list and label each block as [1], [2], etc."""

REALIST_SYSTEM = """You are the "Realist" agent playing a skeptical investor. Your job is to poke holes in each opportunity.
For each opportunity, give 2–3 sentences: point out risks, overestimated market, evidence gaps, competition, execution difficulty. Challenge the Hype view. Keep the same order as the input list and label each block as [1], [2], etc."""

MODERATOR_SYSTEM = """You are the Moderator. You have seen:
1) The original opportunity list
2) Hype's arguments for each
3) Realist's challenges for each

Your task: produce a balanced ScoreCard for each opportunity (same order), considering both sides. Score each dimension 0–5:
- pain_severity, market_size, willingness_to_pay, competition_level, feasibility
Output a ScoreCardList with one ScoreCard per opportunity, in the same order. Do not add commentary; only the structured list."""


class ScoreCardList(BaseModel):
    """One ScoreCard per opportunity, same order."""

    items: list[ScoreCard] = Field(default_factory=list)


def _invoke_text(llm: BaseChatModel, system: str, user: str) -> str:
    """One LLM call returning content as string."""
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=user),
    ]
    resp = llm.invoke(messages)
    return getattr(resp, "content", "") or str(resp)


def run_debate_for_scoring(
    opportunities_text: str,
    num_opportunities: int,
    llm: BaseChatModel,
) -> list[ScoreCard]:
    """
    Run Hype → Realist → Moderator debate and return final ScoreCard list.
    opportunities_text: formatted list of opportunities (theme, evidence, pain points).
    num_opportunities: expected number of items (for validation).
    """
    # 1) Hype argues for each opportunity
    hype_content = _invoke_text(
        llm,
        HYPE_SYSTEM,
        "Opportunities to advocate for:\n\n" + opportunities_text + "\n\nArgue for each in order [1], [2], ...",
    )
    logger.info("Debate: Hype response length=%d", len(hype_content))

    # 2) Realist challenges
    realist_content = _invoke_text(
        llm,
        REALIST_SYSTEM,
        "Hype argued:\n\n" + hype_content + "\n\nAs a skeptical investor, challenge each opportunity. Same order [1], [2], ...",
    )
    logger.info("Debate: Realist response length=%d", len(realist_content))

    # 3) Moderator produces ScoreCards
    moderator_prompt = (
        "Original opportunities:\n\n"
        + opportunities_text
        + "\n\n---\n\nHype:\n\n"
        + hype_content
        + "\n\n---\n\nRealist:\n\n"
        + realist_content
        + "\n\n---\n\nOutput a ScoreCardList (one ScoreCard per opportunity, same order). Each ScoreCard: pain_severity, market_size, willingness_to_pay, competition_level, feasibility (0-5 each)."
    )
    messages = [
        SystemMessage(content=MODERATOR_SYSTEM),
        HumanMessage(content=moderator_prompt),
    ]
    structured = llm.with_structured_output(ScoreCardList)
    result = structured.invoke(messages)

    cards = list(result.items[:num_opportunities]) if result.items else []
    if len(cards) < num_opportunities:
        default = ScoreCard(
            pain_severity=2.5,
            market_size=2.5,
            willingness_to_pay=2.5,
            competition_level=2.5,
            feasibility=2.5,
        )
        cards.extend([default] * (num_opportunities - len(cards)))
    logger.info("Debate: Moderator produced %d ScoreCards", len(cards))
    return cards
