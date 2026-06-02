"""Main LangGraph workflow for GitHub Opportunity Miner."""

from __future__ import annotations

import time
from uuid import uuid4
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from app.config import get_settings
from app.graph.state import GraphState
from app.harness.trace_logger import JsonTraceLogger
from app.nodes.commercial_gap import commercial_gap
from app.nodes.adaptive_query_expand import adaptive_query_expand
from app.nodes.buyer_hypothesis import buyer_hypothesis
from app.nodes.capability_discover import capability_discover
from app.nodes.competitor_scan import competitor_scan
from app.nodes.debate import debate
from app.nodes.evidence_graph_build import evidence_graph_build
from app.nodes.evidence_validate import evidence_validate
from app.nodes.evidence_quality_rank import evidence_quality_rank
from app.nodes.final_judge import final_judge
from app.nodes.fusion_generate import fusion_generate
from app.nodes.fusion_validate import fusion_validate
from app.nodes.github_search_orchestrator import github_search_orchestrator
from app.nodes.intent_detect import intent_detect
from app.nodes.issue_classify import issue_classify
from app.nodes.opportunity_generate import opportunity_generate
from app.nodes.opportunity_dedup import opportunity_dedup
from app.nodes.outreach_targets import outreach_targets
from app.nodes.pain_extract import pain_extract
from app.nodes.query_scope_detect import query_scope_detect
from app.nodes.query_rewrite import query_rewrite
from app.nodes.refinement_response import refinement_response
from app.nodes.report_write import report_write
from app.nodes.research_retrieve import research_retrieve
from app.nodes.search_plan_generate import search_plan_generate
from app.nodes.signal_diagnostics import signal_diagnostics
from app.nodes.startup_memo import startup_memo
from app.nodes.topic_cluster import topic_cluster
from app.nodes.validation_plan import validation_plan
from app.nodes.wtp_signal_detect import wtp_signal_detect


NodeFn = Callable[[GraphState], GraphState]


def _trace_node(node_name: str, fn: NodeFn) -> NodeFn:
    """Wrap a node with JSON trace logging if a trace logger is provided in state."""

    def wrapped(state: GraphState) -> GraphState:
        logger = state.get("_trace_logger")
        observer = state.get("_langfuse_observer")
        progress_callback = state.get("_progress_callback")
        run_id = state.get("run_id", "local")
        start = time.perf_counter()
        errors_before = list(state.get("errors") or [])
        try:
            if callable(progress_callback):
                progress_callback(node_name, "started")
            new_errors: list[str] = []
            if hasattr(observer, "node_span"):
                span_capture: dict[str, Any] = {}
                with observer.node_span(node_name=node_name, input_data=state, output_capture=span_capture):
                    out = fn(state)
                    new_errors = [err for err in out.get("errors", []) if err not in errors_before]
                    span_capture["output"] = out
                    span_capture["errors"] = new_errors
            else:
                out = fn(state)
                new_errors = [err for err in out.get("errors", []) if err not in errors_before]
            latency_ms = (time.perf_counter() - start) * 1000
            out = {
                **out,
                "node_latency_summary": _append_node_latency(
                    state,
                    out,
                    node_name=node_name,
                    latency_ms=latency_ms,
                    errors=new_errors,
                ),
            }
            if isinstance(logger, JsonTraceLogger):
                logger.log(
                    run_id=run_id,
                    node_name=node_name,
                    input_data=state,
                    output_data=out,
                    latency_ms=latency_ms,
                    errors=new_errors,
                    is_mock=get_settings().mock_mode,
                )
            progress_callback = out.get("_progress_callback")
            if callable(progress_callback):
                progress_callback(node_name, "completed")
            return out
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            if isinstance(logger, JsonTraceLogger):
                logger.log(
                    run_id=run_id,
                    node_name=node_name,
                    input_data=state,
                    output_data={},
                    latency_ms=latency_ms,
                    errors=[f"{type(exc).__name__}: {exc}"],
                    is_mock=get_settings().mock_mode,
                )
            raise

    return wrapped


def _append_node_latency(
    state: GraphState,
    out: GraphState,
    *,
    node_name: str,
    latency_ms: float,
    errors: list[str],
) -> list[dict[str, Any]]:
    summary = list(out.get("node_latency_summary") or state.get("node_latency_summary") or [])
    summary.append(
        {
            "node_name": node_name,
            "latency_ms": round(latency_ms, 2),
            "errors_count": len(errors),
            "output_counts": {
                "evidence_items": len(out.get("evidence_items") or []),
                "ranked_evidence_items": len(out.get("ranked_evidence_items") or []),
                "high_value_issues": len(out.get("high_value_issues") or []),
                "pain_points": len(out.get("pain_points") or []),
                "validated_cards": len(out.get("validated_cards") or []),
            },
        }
    )
    return summary


def _search_quality_gate(state: GraphState) -> str:
    ranked = state.get("ranked_evidence_items") or []
    repo_coverage_count = len(state.get("selected_repos") or [])
    valid_evidence_count = len(ranked or state.get("evidence_items") or [])
    iteration_count = state.get("iteration_count") or 0
    expansion_budget = int((state.get("search_plan") or {}).get("expansion_budget") or 0)
    strong_count = len([item for item in ranked if float(item.get("evidence_quality_score") or 0) >= 8])
    if strong_count >= 8:
        return "issue_classify"
    if repo_coverage_count >= 3 and valid_evidence_count >= 15:
        return "issue_classify"
    if expansion_budget <= 0:
        return "issue_classify"
    return "adaptive_query_expand"


def _after_evidence_validate(state: GraphState) -> str:
    if state.get("skip_debate"):
        return "buyer_hypothesis"
    return "debate"


def _normalize_run_mode(state: GraphState) -> str:
    mode = str(state.get("run_mode") or "standard").lower()
    if mode not in {"quick", "standard", "deep"}:
        return "standard"
    return mode


def _after_card_validation(state: GraphState) -> str:
    if not state.get("validated_cards"):
        return "report_write"
    mode = _normalize_run_mode(state)
    if mode == "quick":
        return "report_write"
    if mode == "standard":
        return "debate"
    return "evidence_graph_build"


def _after_query_scope(state: GraphState) -> str:
    if state.get("refinement_required"):
        return "refinement_response"
    return "intent_detect"


def _after_search_plan_generate(state: GraphState) -> str:
    if state.get("warm_start_evidence") and (state.get("evidence_pool") or state.get("evidence_items")):
        return "evidence_quality_rank"
    return "github_search_orchestrator"


def build_graph(trace_logger: JsonTraceLogger | None = None):
    graph = StateGraph(GraphState)

    graph.add_node("query_rewrite", _trace_node("query_rewrite", query_rewrite))
    graph.add_node("query_scope_detect", _trace_node("query_scope_detect", query_scope_detect))
    graph.add_node("refinement_response", _trace_node("refinement_response", refinement_response))
    graph.add_node("intent_detect", _trace_node("intent_detect", intent_detect))
    graph.add_node("search_plan_generate", _trace_node("search_plan_generate", search_plan_generate))
    graph.add_node("github_search_orchestrator", _trace_node("github_search_orchestrator", github_search_orchestrator))
    graph.add_node("evidence_quality_rank", _trace_node("evidence_quality_rank", evidence_quality_rank))
    graph.add_node("adaptive_query_expand", _trace_node("adaptive_query_expand", adaptive_query_expand))
    graph.add_node("issue_classify", _trace_node("issue_classify", issue_classify))
    graph.add_node("pain_extract", _trace_node("pain_extract", pain_extract))
    graph.add_node("topic_cluster", _trace_node("topic_cluster", topic_cluster))
    graph.add_node("commercial_gap", _trace_node("commercial_gap", commercial_gap))
    graph.add_node("opportunity_generate", _trace_node("opportunity_generate", opportunity_generate))
    graph.add_node("opportunity_dedup", _trace_node("opportunity_dedup", opportunity_dedup))
    graph.add_node("evidence_validate", _trace_node("evidence_validate", evidence_validate))
    graph.add_node("signal_diagnostics", _trace_node("signal_diagnostics", signal_diagnostics))
    graph.add_node("evidence_graph_build", _trace_node("evidence_graph_build", evidence_graph_build))
    graph.add_node("capability_discover", _trace_node("capability_discover", capability_discover))
    graph.add_node("research_retrieve", _trace_node("research_retrieve", research_retrieve))
    graph.add_node("fusion_generate", _trace_node("fusion_generate", fusion_generate))
    graph.add_node("fusion_validate", _trace_node("fusion_validate", fusion_validate))
    graph.add_node("debate", _trace_node("debate", debate))
    graph.add_node("buyer_hypothesis", _trace_node("buyer_hypothesis", buyer_hypothesis))
    graph.add_node("wtp_signal_detect", _trace_node("wtp_signal_detect", wtp_signal_detect))
    graph.add_node("competitor_scan", _trace_node("competitor_scan", competitor_scan))
    graph.add_node("outreach_targets", _trace_node("outreach_targets", outreach_targets))
    graph.add_node("validation_plan", _trace_node("validation_plan", validation_plan))
    graph.add_node("final_judge", _trace_node("final_judge", final_judge))
    graph.add_node("startup_memo", _trace_node("startup_memo", startup_memo))
    graph.add_node("report_write", _trace_node("report_write", report_write))

    graph.add_edge(START, "query_rewrite")
    graph.add_edge("query_rewrite", "query_scope_detect")
    graph.add_conditional_edges(
        "query_scope_detect",
        _after_query_scope,
        {"intent_detect": "intent_detect", "refinement_response": "refinement_response"},
    )
    graph.add_edge("refinement_response", END)
    graph.add_edge("intent_detect", "search_plan_generate")
    graph.add_conditional_edges(
        "search_plan_generate",
        _after_search_plan_generate,
        {"github_search_orchestrator": "github_search_orchestrator", "evidence_quality_rank": "evidence_quality_rank"},
    )
    graph.add_edge("github_search_orchestrator", "evidence_quality_rank")
    graph.add_conditional_edges(
        "evidence_quality_rank",
        _search_quality_gate,
        {"issue_classify": "issue_classify", "adaptive_query_expand": "adaptive_query_expand"},
    )
    graph.add_edge("adaptive_query_expand", "github_search_orchestrator")
    graph.add_edge("issue_classify", "pain_extract")
    graph.add_edge("pain_extract", "topic_cluster")
    graph.add_edge("topic_cluster", "commercial_gap")
    graph.add_edge("commercial_gap", "opportunity_generate")
    graph.add_edge("opportunity_generate", "opportunity_dedup")
    graph.add_edge("opportunity_dedup", "evidence_validate")
    graph.add_edge("evidence_validate", "signal_diagnostics")
    graph.add_conditional_edges(
        "signal_diagnostics",
        _after_card_validation,
        {"evidence_graph_build": "evidence_graph_build", "debate": "debate", "report_write": "report_write"},
    )
    graph.add_edge("evidence_graph_build", "capability_discover")
    graph.add_edge("capability_discover", "research_retrieve")
    graph.add_edge("research_retrieve", "fusion_generate")
    graph.add_edge("fusion_generate", "fusion_validate")
    graph.add_conditional_edges(
        "fusion_validate",
        _after_evidence_validate,
        {"debate": "debate", "buyer_hypothesis": "buyer_hypothesis"},
    )
    graph.add_edge("debate", "buyer_hypothesis")
    graph.add_edge("buyer_hypothesis", "wtp_signal_detect")
    graph.add_edge("wtp_signal_detect", "competitor_scan")
    graph.add_edge("competitor_scan", "outreach_targets")
    graph.add_edge("outreach_targets", "validation_plan")
    graph.add_edge("validation_plan", "final_judge")
    graph.add_edge("final_judge", "startup_memo")
    graph.add_edge("startup_memo", "report_write")
    graph.add_edge("report_write", END)
    return graph.compile()


def run_graph(
    topic: str,
    *,
    trace_logger: JsonTraceLogger | None = None,
    initial_state: dict[str, Any] | None = None,
    langfuse_observer: Any | None = None,
) -> GraphState:
    """Run the full mock graph for a topic."""
    run_id = str(uuid4())
    initial: GraphState = {
        "run_id": run_id,
        "user_query": topic,
        "errors": [],
        "iteration_count": 0,
    }
    if initial_state:
        initial.update(initial_state)
        initial.setdefault("run_id", run_id)
        initial.setdefault("user_query", topic)
        initial.setdefault("errors", [])
        initial.setdefault("iteration_count", 0)
    if trace_logger is not None:
        initial["_trace_logger"] = trace_logger  # type: ignore[typeddict-unknown-key]
    if langfuse_observer is not None:
        initial["_langfuse_observer"] = langfuse_observer  # type: ignore[typeddict-unknown-key]
    graph = build_graph(trace_logger=trace_logger)
    final_state = graph.invoke(initial)
    final_state.pop("_trace_logger", None)
    final_state.pop("_langfuse_observer", None)
    final_state.pop("_progress_callback", None)
    return final_state
