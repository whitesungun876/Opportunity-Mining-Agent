"""Run-level and per-node evaluation metrics."""

from __future__ import annotations

from typing import Any


def rejection_rate(validated_count: int, total_count: int) -> float:
    """Rejection rate = 1 - (validated / total)."""
    if total_count <= 0:
        return 0.0
    return 1.0 - (validated_count / total_count)


def denoise_ratio(raw_count: int, cleaned_count: int) -> float:
    """Denoise ratio: cleaned / raw; lower means more aggressive filtering."""
    if raw_count <= 0:
        return 1.0
    return cleaned_count / raw_count


def schema_compliance_rate(valid_items: int, total_items: int) -> float:
    """Schema compliance: share of items that parse as Pydantic models."""
    if total_items <= 0:
        return 1.0
    return valid_items / total_items


def compute_run_metrics(state: dict[str, Any]) -> dict[str, float]:
    """Aggregate run-level metrics from final state."""
    raw = len(state.get("raw_items") or [])
    cleaned = len(state.get("cleaned_texts") or state.get("clean_comments") or [])
    opportunities = state.get("opportunities") or state.get("opportunity_clusters") or []
    validated = state.get("validated_opportunities") or state.get("validated_cards") or []
    return {
        "denoise_ratio": denoise_ratio(raw, len(cleaned)),
        "rejection_rate": rejection_rate(len(validated), len(opportunities)) if opportunities else 0.0,
        "opportunities_count": len(opportunities),
        "validated_count": len(validated),
    }


def compute_run_report(
    state: dict[str, Any],
    node_timings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Full run evaluation report: run-level metrics, per-node metrics, and node timings.
    node_timings should be from observability.get_node_run_records() after the run.
    """
    from src.eval.node_metrics import compute_node_metrics

    report: dict[str, Any] = {
        "run": compute_run_metrics(state),
        "node_metrics": compute_node_metrics(state),
    }
    if node_timings is not None:
        report["node_timings"] = node_timings
    return report
