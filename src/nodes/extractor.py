"""Structured pain-point extraction (schema-based) via LLM."""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, ValidationError

from src.utils.schema import PainPoint
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SEC = 2.0


class PainPointList(BaseModel):
    """Wrapper for LLM structured output: list of PainPoint."""

    items: list[PainPoint] = Field(default_factory=list)


SYSTEM_PROMPT = """You are a business analyst. The user will give you a batch of social media or product comments.
Your task is to extract supply–demand mismatch pain points (concrete pain points), not abstract nouns.

Requirements:
1) Output must be a PainPoint list (items).
2) Each PainPoint must be specific: who + in what situation + why (cause) + what they complain about + what action intent (e.g. want to switch, seek alternative, willing to pay).
3) evidence must be verbatim quotes from the input text (do not paraphrase or invent).
4) If you cannot find clear evidence for a point, do not output that PainPoint.
5) Ignore purely positive or low-signal comments (e.g. "best ever" / "so good" with no concrete complaint).
"""


def _validate_pain_point(item: Any, raw_content: str) -> PainPoint | None:
    """
    Re-validate a single item as PainPoint and check evidence is in source text.
    Returns the PainPoint if valid, else None.
    """
    try:
        if isinstance(item, PainPoint):
            p = item
        else:
            p = PainPoint.model_validate(item)
    except (ValidationError, TypeError):
        return None
    if not p.complaint or not p.evidence:
        return None
    if not all(isinstance(ev, str) and ev.strip() for ev in p.evidence):
        return None
    if not all(ev in raw_content for ev in p.evidence):
        return None
    return p


def extract(state: dict[str, Any], max_retries: int | None = None) -> dict[str, Any]:
    """
    Extract PainPoint list from raw comments using GPT-4o structured output.
    Input: state['clean_comments'] (from cleaner); fallback: state['cleaned_texts'], state['raw_comments'].
    Writes state['pain_points'] and state['extracted_pains'] (unified contract alias).
    Uses try/except, automatic retries, and schema validation.
    """
    # Primary input: clean_comments (cleaner output for extractor)
    comments_for_extract: list[str] = (
        state.get("clean_comments") or state.get("cleaned_texts") or state.get("raw_comments") or []
    )
    raw_content = "\n".join(comments_for_extract).strip()

    if not raw_content:
        logger.info("Extractor: no input text, returning empty pain_points")
        return {**state, "pain_points": [], "extracted_pains": []}

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Text to analyze:\n{raw_content}"),
    ]
    llm_factory = state.get("_llm_factory")  # allow test injection
    model, temperature = "gpt-4o", 0
    llm = llm_factory() if llm_factory else ChatOpenAI(model=model, temperature=temperature)
    structured_llm = llm.with_structured_output(PainPointList)

    retries = max(1, max_retries if max_retries is not None else MAX_RETRIES)
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            result: PainPointList = structured_llm.invoke(messages)
            # Schema validation + evidence check per item
            filtered_items: list[PainPoint] = []
            for item in result.items:
                p = _validate_pain_point(item, raw_content)
                if p is not None:
                    filtered_items.append(p)
            logger.info(
                "Extractor: clean_comments=%d, pain_points=%d (attempt %d)",
                len(comments_for_extract),
                len(filtered_items),
                attempt + 1,
            )
            return {**state, "pain_points": filtered_items, "extracted_pains": filtered_items}
        except ValidationError as e:
            last_error = e
            logger.warning("Extractor: schema validation failed (attempt %d): %s", attempt + 1, e)
        except Exception as e:
            last_error = e
            logger.warning("Extractor: invoke failed (attempt %d): %s", attempt + 1, e)
        if attempt < retries - 1:
            time.sleep(RETRY_DELAY_SEC)

    logger.error("Extractor: all %d retries failed; last error: %s", retries, last_error)
    return {
        **state,
        "pain_points": [],
        "extracted_pains": [],
        "error": f"Extractor failed after {retries} retries: {last_error!s}",
    }


def _quality_score(pains: list[PainPoint], num_comments: int) -> float:
    """Simple quality signal: 0 if no pains, else increases with count and coverage."""
    if not pains:
        return 0.0
    coverage = len(pains) / max(1, num_comments)
    return min(1.0, 0.2 + 0.15 * len(pains) + 0.2 * coverage)


def extractor_node(
    state: dict[str, Any],
    *,
    max_retries: int = 2,
    min_items_required: int = 0,
) -> dict[str, Any]:
    """
    Extractor node for tests and standalone use.
    Returns dict with extracted_pains, pain_points, and quality_score.
    """
    out = extract(state, max_retries=max_retries)
    pains = out.get("pain_points", [])
    # Same as extract: clean_comments (cleaner output for extractor)
    comments = state.get("clean_comments") or state.get("cleaned_texts") or state.get("raw_comments") or []
    score = _quality_score(pains, len(comments))
    return {
        **out,
        "extracted_pains": pains,
        "pain_points": pains,
        "quality_score": score,
    }
