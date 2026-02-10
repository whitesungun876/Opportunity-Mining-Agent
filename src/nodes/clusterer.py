"""Theme clustering: merge pain points into opportunity clusters (LLM for concept merging).

Optional: ORACLE_USE_VECTOR_MEMORY=1 enables long-term pain memory — current pains are
embedded and stored, then similar past pains are retrieved and added to the LLM context
to reduce context window pressure on large text.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.utils.schema import OpportunityCluster, PainPoint
from src.utils.logger import get_logger

logger = get_logger(__name__)

VECTOR_MEMORY_TOP_K = 10
MAX_MEMORY_CONTEXT_CHARS = 2000

CLUSTER_SYSTEM = """You are an opportunity analyst. Given a list of pain points (complaint, cause, persona, evidence),
merge them into a smaller list of opportunity themes. Each theme should abstract and unify similar complaints
(e.g. "too expensive", "subscription feels like a rip-off", "monthly fee is a turn-off" -> theme "high subscription cost"). Output a ClusterList with items: list of OpportunityCluster.
Each OpportunityCluster: theme (short label), pain_points (subset of input), sample_size (sum of evidence counts), confidence (0-1).
If "Long-term memory (similar past pains)" is provided, use it only as context to inform theme naming and grouping; do not duplicate those items into your output clusters."""


class ClusterList(BaseModel):
    """Wrapper for LLM structured output: list of OpportunityCluster."""

    items: list[OpportunityCluster] = Field(default_factory=list)


def cluster(state: dict[str, Any]) -> dict[str, Any]:
    """
    Cluster pain_points into opportunity themes (OpportunityCluster).
    Input: state['pain_points'], state['canon_comments'] (from cleaner, for cluster).
    """
    points: list[PainPoint] = state.get("pain_points") or []
    canon_comments: list[str] = state.get("canon_comments") or []
    opportunities: list[OpportunityCluster] = []
    # Placeholder: group by complaint prefix; real impl can use embedding + clustering on canon_comments
    by_theme: dict[str, list[PainPoint]] = {}
    for p in points:
        theme = (p.complaint[:30] + "…") if len(p.complaint) > 30 else (p.complaint or "default")
        by_theme.setdefault(theme, []).append(p)
    for theme, group in by_theme.items():
        opportunities.append(
            OpportunityCluster(
                theme=theme,
                pain_points=group,
                sample_size=sum(len(p.evidence) for p in group),
                confidence=0.5,
            )
        )
    logger.info(
        "Clusterer: pain_points=%d, canon_comments=%d (input), opportunities=%d",
        len(points),
        len(canon_comments),
        len(opportunities),
    )
    return {**state, "opportunities": opportunities, "opportunity_clusters": opportunities}


def _pain_to_text(p: PainPoint) -> str:
    """One line summary for embedding and retrieval."""
    parts = [p.complaint or "", p.cause or ""]
    if getattr(p, "evidence", None):
        parts.append(" ".join((p.evidence or [])[:2]))
    return " | ".join(x.strip() for x in parts if x.strip())[:500]


def _store_pains_and_retrieve_similar(
    state: dict[str, Any],
    pains: list[PainPoint],
    topic: str,
    top_k: int = VECTOR_MEMORY_TOP_K,
) -> str:
    """Store current pain texts in vector DB, then retrieve similar past pains for context. Returns a string to append to the LLM prompt."""
    try:
        from src.memory.vector_db import get_vector_store, add_pain_texts, query_similar_pains
    except ImportError:
        return ""
    store = get_vector_store(state.get("_chroma_persist_dir") or os.getenv("CHROMA_PERSIST_DIR"))
    if store is None:
        return ""
    documents = [_pain_to_text(p) for p in pains]
    if not documents:
        return ""
    query_parts = documents[:5]
    query_text = "\n".join(query_parts)[:800]
    similar = query_similar_pains(store, query_text, n_results=top_k, topic_filter=None)
    ids = [str(uuid.uuid4()) for _ in documents]
    metadatas = [{"topic": topic or ""}] * len(documents)
    add_pain_texts(store, ids, documents, metadatas)
    if not similar:
        return ""
    memory_lines = [item.get("document", "") for item in similar if item.get("document")]
    if not memory_lines:
        return ""
    block = "\n".join(memory_lines)[:MAX_MEMORY_CONTEXT_CHARS]
    return f"\n\nLong-term memory (similar past pains, for context only):\n{block}"


def clusterer_node(state: dict[str, Any], *, max_retries: int = 0) -> dict[str, Any]:
    """
    Clusterer node: uses LLM to merge pain points into opportunity themes (concept merging).
    Fallback to rule-based cluster() when state["_cluster_rule_only"] is True or LLM fails.
    Optional: when ORACLE_USE_VECTOR_MEMORY=1, stores pain embeddings and retrieves similar past pains to augment the LLM context.
    """
    pains: list[PainPoint] = state.get("extracted_pains") or state.get("pain_points") or []
    if not pains:
        return {**state, "opportunity_clusters": [], "opportunities": []}

    use_rule_only = state.get("_cluster_rule_only") is True
    if use_rule_only:
        out = cluster({**state, "pain_points": pains})
        clusters = out.get("opportunities", [])
        return {**state, "opportunity_clusters": clusters, "opportunities": clusters}

    use_vector_memory = state.get("_use_vector_memory") is True or (os.getenv("ORACLE_USE_VECTOR_MEMORY", "").strip() == "1")
    memory_context = ""
    if use_vector_memory:
        topic = (state.get("topic") or "").strip()
        memory_context = _store_pains_and_retrieve_similar(state, pains, topic, top_k=VECTOR_MEMORY_TOP_K)
        if memory_context:
            logger.info("Clusterer: added vector memory context (%d chars)", len(memory_context))

    llm_factory = state.get("_llm_factory")
    llm = llm_factory() if llm_factory else ChatOpenAI(model="gpt-4o", temperature=0)
    pains_text = json.dumps([p.model_dump() for p in pains], ensure_ascii=False, indent=0)
    user_content = f"Pain points to cluster:\n{pains_text}{memory_context}"
    messages = [
        SystemMessage(content=CLUSTER_SYSTEM),
        HumanMessage(content=user_content),
    ]
    try:
        structured = llm.with_structured_output(ClusterList)
        result = structured.invoke(messages)
        clusters = result.items
    except Exception as e:
        logger.warning("Clusterer LLM failed, falling back to rule-based: %s", e)
        out = cluster({**state, "pain_points": pains})
        clusters = out.get("opportunities", [])
    return {**state, "opportunity_clusters": clusters, "opportunities": clusters}
