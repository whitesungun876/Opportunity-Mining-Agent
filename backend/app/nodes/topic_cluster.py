"""Pain topic clustering node using embeddings with deterministic fallback."""

from __future__ import annotations

from app.config import get_settings
from app.graph.state import GraphState
from app.services.clustering import cluster_pain_points
from app.services.embedding_client import EmbeddingClient


def _cluster_matched_signals(cluster: dict, evidence_items: list[dict]) -> list[str]:
    evidence_ids = {str(evidence_id) for evidence_id in cluster.get("evidence_ids") or []}
    signals: list[str] = []
    for item in evidence_items:
        if str(item.get("evidence_id")) not in evidence_ids:
            continue
        for signal in item.get("matched_signals") or []:
            signals.append(str(signal))
    if not signals and cluster.get("pain_type"):
        signals.append(str(cluster.get("pain_type")).replace("_", " "))
    return list(dict.fromkeys(signals))[:8]


def _cluster_rejection_reason(cluster: dict) -> str | None:
    evidence_count = int(cluster.get("evidence_count") or len(cluster.get("evidence_ids") or []))
    severity = float(cluster.get("severity_score") or 0)
    repetition = float(cluster.get("repetition_score") or 0)
    if evidence_count < 3:
        return "fewer than 3 linked evidence items"
    if severity < 0.55 and repetition < 0.4:
        return "weak severity and repetition signals"
    return None


def _apply_cluster_quality_gate(clusters: list[dict], evidence_items: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    evidence_items = evidence_items or []
    kept: list[dict] = []
    rejected: list[dict] = []
    for cluster in clusters:
        enriched = {
            **cluster,
            "matched_signals": _cluster_matched_signals(cluster, evidence_items),
        }
        reason = _cluster_rejection_reason(cluster)
        if reason:
            rejected.append({**enriched, "rejection_reason": reason})
        else:
            kept.append(enriched)
    kept.sort(
        key=lambda item: (
            int(item.get("evidence_count") or len(item.get("evidence_ids") or [])),
            float(item.get("repetition_score") or 0),
            float(item.get("severity_score") or 0),
        ),
        reverse=True,
    )
    return kept, rejected


def topic_cluster(state: GraphState) -> GraphState:
    with EmbeddingClient() as client:
        clusters = cluster_pain_points(
            state.get("pain_points") or [],
            evidence_items=state.get("evidence_items") or [],
            embedding_client=client,
        )
    rejected_clusters: list[dict] = []
    if not get_settings().mock_mode:
        clusters, rejected_clusters = _apply_cluster_quality_gate(clusters, state.get("evidence_items") or [])
    topics = [
        {
            "topic_id": item["cluster_id"],
            "theme": item["theme"],
            "pain_type": item.get("pain_type"),
            "evidence_count": item.get("evidence_count", 0),
        }
        for item in clusters
    ]
    return {
        **state,
        "pain_clusters": clusters,
        "rejected_pain_clusters": rejected_clusters,
        "pain_topics": topics,
    }
