"""Core orchestration: State definition, node registration, conditional edges."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from src.utils.observability import wrap_node
from src.utils.policy_gates import get_policy_gate_decision
from src.utils.schema import OpportunityCluster, PainPoint, ScoreCard

# ---------- State ----------


class GraphState(TypedDict, total=False):
    """Graph state: field contract for each node."""

    # Input: research subject (single source of truth)
    topic: str
    raw_items: list[dict]
    # Cleaner output: clean_comments -> extractor, canon_comments -> clusterer
    raw_comments: list[str]
    clean_comments: list[str]
    canon_comments: list[str]
    cleaned_texts: list[str]  # backward compat
    dropped_comments: list[dict]
    dedup_groups: list[dict]
    clean_stats: dict
    # Extractor
    extracted_pains: list[PainPoint]
    pain_points: list[PainPoint]  # backward compat
    # Cluster & validate
    opportunity_clusters: list[OpportunityCluster]
    opportunities: list[OpportunityCluster]  # backward compat
    opportunity_cards: list[dict]
    validated_opportunities: list[OpportunityCluster]
    validated_cards: list[dict]
    rejected_cards: list[dict]
    validation_summary: dict
    is_validated: bool
    needs_retry: bool
    iteration_count: int
    # Policy gates
    total_items: int
    max_total_items: int
    previous_evidence_count: int
    current_evidence_count: int
    low_novelty_ratio: float
    # Streaming collect: batches to process one-by-one (clean+extract per batch)
    _collect_batches: list[list[str]]
    _collect_index: int
    # Score & output
    score_cards: list[ScoreCard]
    report: str
    final_report: str | dict
    error: str
    status: str


# ---------- Node wrappers (logic in nodes/) ----------


def _collector(state: GraphState) -> GraphState:
    from src.nodes.collector import collect
    return collect(state)


def _cleaner(state: GraphState) -> GraphState:
    from src.nodes.cleaner import clean
    return clean(state)


def _extractor(state: GraphState) -> GraphState:
    from src.nodes.extractor import extract
    return extract(state)


def _clusterer(state: GraphState) -> GraphState:
    from src.nodes.clusterer import clusterer_node
    return clusterer_node(state)


def _validator(state: GraphState) -> GraphState:
    from src.nodes.validator import validate
    return validate(state)


def _scorer(state: GraphState) -> GraphState:
    from src.nodes.scorer import score
    return score(state)


def _reporter(state: GraphState) -> GraphState:
    from src.nodes.reporter import report
    return report(state)


def _memory(state: GraphState) -> GraphState:
    from src.nodes.memory_node import memory
    return memory(state)


def _carder(state: GraphState) -> GraphState:
    from src.nodes.reporter import cards
    return cards(state)


def _process_batch(state: GraphState) -> GraphState:
    from src.nodes.streaming import process_batch
    return process_batch(state)


def _after_collect(state: GraphState) -> str:
    """If streaming batches present, go to process_batch; else clean."""
    batches = state.get("_collect_batches") or []
    if batches and len(batches) > 0:
        return "process_batch"
    return "clean"


def _after_process_batch(state: GraphState) -> str:
    """If more batches, loop to process_batch; else cluster."""
    batches = state.get("_collect_batches") or []
    idx = state.get("_collect_index") or 0
    if idx < len(batches):
        return "process_batch"
    return "cluster"


def _after_validate(state: GraphState) -> str:
    """Route by policy gates: STOP (report), retry (collect), or proceed (score)."""
    edge, reason = get_policy_gate_decision(state)
    from src.utils.logger import get_logger
    get_logger(__name__).info("Policy gate: %s (%s)", edge, reason)
    return edge


def build_graph():
    """Build and compile LangGraph; returns compiled graph so callers don't need to .compile()."""
    graph = StateGraph(GraphState)

    graph.add_node("collect", wrap_node("collect", _collector))
    graph.add_node("process_batch", wrap_node("process_batch", _process_batch))
    graph.add_node("clean", wrap_node("clean", _cleaner))
    graph.add_node("extract", wrap_node("extract", _extractor))
    graph.add_node("cluster", wrap_node("cluster", _clusterer))
    graph.add_node("cards", wrap_node("cards", _carder))
    graph.add_node("validate", wrap_node("validate", _validator))
    graph.add_node("score", wrap_node("score", _scorer))
    graph.add_node("memory", wrap_node("memory", _memory))
    graph.add_node("report", wrap_node("report", _reporter))

    graph.set_entry_point("collect")
    graph.add_conditional_edges("collect", _after_collect, {"process_batch": "process_batch", "clean": "clean"})
    graph.add_conditional_edges("process_batch", _after_process_batch, {"process_batch": "process_batch", "cluster": "cluster"})
    graph.add_edge("clean", "extract")
    graph.add_edge("extract", "cluster")
    graph.add_edge("cluster", "cards")
    graph.add_edge("cards", "validate")
    graph.add_conditional_edges("validate", _after_validate, {"collect": "collect", "score": "score", "report": "report"})
    graph.add_edge("score", "memory")
    graph.add_edge("memory", "report")
    graph.add_edge("report", END)

    return graph.compile()
