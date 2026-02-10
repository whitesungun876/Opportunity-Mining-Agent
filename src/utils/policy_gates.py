"""Policy gates: decide when to STOP (report), continue (collect), or proceed to score.

Summary:
1. Iteration Gate   - iteration_count >= MAX_ITER → STOP
2. Quality Gate     - validated_pass_ratio >= QUALITY_GATE_PASS_RATIO → STOP (good enough)
3. Evidence Saturation Gate - new_evidence_ratio < EVIDENCE_SATURATION → STOP
4. Budget Gate      - total_items >= max_total_items → STOP
5. Memory Novelty Gate - low_novelty_ratio > MEMORY_LOW_NOVELTY → STOP
"""

from __future__ import annotations

import os
from typing import Any

# Config (env overrides)
MAX_ITER = int(os.getenv("ORACLE_MAX_ITER", "5"))
QUALITY_GATE_PASS_RATIO = float(os.getenv("ORACLE_QUALITY_GATE_PASS_RATIO", "0.7"))
EVIDENCE_SATURATION = float(os.getenv("ORACLE_EVIDENCE_SATURATION", "0.1"))
BUDGET_MAX_TOTAL_ITEMS = int(os.getenv("ORACLE_MAX_TOTAL_ITEMS", "500"))
MEMORY_LOW_NOVELTY = float(os.getenv("ORACLE_MEMORY_LOW_NOVELTY", "0.6"))


def _validated_pass_ratio(state: dict[str, Any]) -> float | None:
    summary = state.get("validation_summary") or {}
    total = summary.get("total")
    passed = summary.get("passed")
    if total is None or passed is None or total <= 0:
        return None
    return passed / total


def _new_evidence_ratio(state: dict[str, Any]) -> float | None:
    """Ratio of new evidence this round vs previous; None if not computable."""
    current = state.get("current_evidence_count")
    previous = state.get("previous_evidence_count")
    if current is None:
        return None
    if previous is None or previous <= 0:
        return 1.0  # first run: treat as full novelty
    if current <= 0:
        return 0.0
    new_count = max(0, current - previous)
    return new_count / max(previous, 1)


def get_policy_gate_decision(state: dict[str, Any]) -> tuple[str, str]:
    """
    Evaluate policy gates in order. Returns (edge, reason).
    edge: "report" (hard STOP, skip score) | "score" (STOP loop but run score→memory→report) | "collect" (retry).
    """
    iteration_count = state.get("iteration_count") or 0
    total_items = state.get("total_items") or 0
    max_total_items = state.get("max_total_items") or BUDGET_MAX_TOTAL_ITEMS
    low_novelty_ratio = state.get("low_novelty_ratio")
    needs_retry = state.get("needs_retry") is True

    # 1. Iteration Gate → STOP (go to score so we still run score→memory→report)
    if iteration_count >= MAX_ITER:
        return ("score", f"iteration_count >= MAX_ITER ({iteration_count} >= {MAX_ITER})")

    # 2. Quality Gate → STOP (good enough)
    ratio = _validated_pass_ratio(state)
    if ratio is not None and ratio >= QUALITY_GATE_PASS_RATIO:
        return ("score", f"validated_pass_ratio >= {QUALITY_GATE_PASS_RATIO} ({ratio:.2f})")

    # 3. Evidence Saturation Gate → STOP
    new_ev = _new_evidence_ratio(state)
    if new_ev is not None and new_ev < EVIDENCE_SATURATION:
        return ("score", f"new_evidence_ratio < {EVIDENCE_SATURATION} ({new_ev:.2f})")

    # 4. Budget Gate → STOP
    if total_items >= max_total_items:
        return ("score", f"total_items >= max_total_items ({total_items} >= {max_total_items})")

    # 5. Memory Novelty Gate → STOP
    if low_novelty_ratio is not None and low_novelty_ratio > MEMORY_LOW_NOVELTY:
        return ("score", f"low_novelty_ratio > {MEMORY_LOW_NOVELTY} ({low_novelty_ratio:.2f})")

    # No gate triggered: route by needs_retry
    if needs_retry:
        return ("collect", "needs_retry")
    return ("score", "proceed_to_score")
