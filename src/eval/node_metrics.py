"""Per-node evaluation metrics (1-3 core metrics per node)."""

from __future__ import annotations

from typing import Any

from src.eval.metrics import denoise_ratio, rejection_rate


def metrics_collect(state: dict[str, Any]) -> dict[str, Any]:
    """collect: raw item count and presence of topic."""
    raw = state.get("raw_items") or []
    return {
        "raw_count": len(raw),
        "has_topic": (state.get("topic") or "").strip() != "",
    }


def metrics_clean(state: dict[str, Any]) -> dict[str, Any]:
    """clean: counts and denoise ratio."""
    raw = state.get("raw_items") or state.get("raw_comments") or []
    cleaned = state.get("clean_comments") or state.get("cleaned_texts") or []
    dropped = state.get("dropped_comments") or []
    raw_n = len(raw) if raw else 0
    cleaned_n = len(cleaned)
    return {
        "raw_count": raw_n,
        "cleaned_count": cleaned_n,
        "dropped_count": len(dropped),
        "denoise_ratio": denoise_ratio(raw_n, cleaned_n) if raw_n else 1.0,
    }


def metrics_extract(state: dict[str, Any]) -> dict[str, Any]:
    """extract: pain point count."""
    pains = state.get("extracted_pains") or state.get("pain_points") or []
    return {
        "pain_count": len(pains),
    }


def metrics_cluster(state: dict[str, Any]) -> dict[str, Any]:
    """cluster: cluster count and average confidence."""
    clusters = state.get("opportunity_clusters") or state.get("opportunities") or []
    n = len(clusters)
    if n == 0:
        return {"cluster_count": 0, "avg_confidence": 0.0}
    confs = [getattr(c, "confidence", 0.0) for c in clusters if hasattr(c, "confidence")]
    avg = sum(confs) / len(confs) if confs else 0.0
    return {
        "cluster_count": n,
        "avg_confidence": round(avg, 3),
    }


def metrics_cards(state: dict[str, Any]) -> dict[str, Any]:
    """cards: card count (same as cluster output typically)."""
    cards = state.get("opportunity_cards") or []
    return {"card_count": len(cards)}


def metrics_validate(state: dict[str, Any]) -> dict[str, Any]:
    """validate: passed/total and rejection rate, quality score."""
    summary = state.get("validation_summary") or {}
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    quality = summary.get("quality_score", 0.0)
    validated = state.get("validated_cards") or state.get("validated_opportunities") or []
    return {
        "total": total,
        "passed": len(validated) if validated else passed,
        "rejection_rate": rejection_rate(passed, total) if total else 0.0,
        "quality_score": quality,
    }


def metrics_score(state: dict[str, Any]) -> dict[str, Any]:
    """score: count and average total_score."""
    cards = state.get("score_cards") or []
    n = len(cards)
    if n == 0:
        return {"score_count": 0, "avg_total_score": 0.0}
    totals = [getattr(sc, "total_score", None) for sc in cards]
    totals = [t for t in totals if t is not None]
    avg = sum(totals) / len(totals) if totals else 0.0
    return {
        "score_count": n,
        "avg_total_score": round(avg, 2),
    }


def metrics_memory(state: dict[str, Any]) -> dict[str, Any]:
    """memory: no in-state counter; report what we could persist (theme count)."""
    validated = state.get("validated_cards") or state.get("validated_opportunities") or []
    return {"opportunities_eligible": len(validated)}


def metrics_report(state: dict[str, Any]) -> dict[str, Any]:
    """report: presence and length."""
    report = state.get("report") or state.get("final_report") or ""
    if isinstance(report, dict):
        report = str(report)
    return {
        "has_report": bool(report),
        "report_length": len(report) if isinstance(report, str) else 0,
    }


NODE_METRIC_FUNCS = {
    "collect": metrics_collect,
    "clean": metrics_clean,
    "extract": metrics_extract,
    "cluster": metrics_cluster,
    "cards": metrics_cards,
    "validate": metrics_validate,
    "score": metrics_score,
    "memory": metrics_memory,
    "report": metrics_report,
}


def compute_node_metrics(state: dict[str, Any], nodes: list[str] | None = None) -> dict[str, dict[str, Any]]:
    """Compute metrics for each node from final state. If nodes is None, run all known nodes."""
    nodes = nodes or list(NODE_METRIC_FUNCS)
    out: dict[str, dict[str, Any]] = {}
    for name in nodes:
        fn = NODE_METRIC_FUNCS.get(name)
        if fn:
            try:
                out[name] = fn(state)
            except Exception:
                out[name] = {}
    return out
