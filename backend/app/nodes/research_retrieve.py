"""Research evidence retrieval node."""

from __future__ import annotations

from app.fusion.research_retriever import retrieve_research_evidence
from app.graph.state import GraphState


def research_retrieve(state: GraphState) -> GraphState:
    research = retrieve_research_evidence(state)
    return {
        **state,
        "research_evidence": research,
    }
