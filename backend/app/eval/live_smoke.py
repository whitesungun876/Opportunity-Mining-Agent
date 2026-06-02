"""Live smoke runner with validation diagnostics.

This script is intentionally thin: it uses the normal graph and only adds
human-readable diagnostics around evidence validation results.
"""

from __future__ import annotations

import argparse
import json
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.nodes.commercial_gap import commercial_gap
from app.nodes.debate import debate
from app.nodes.evidence_validate import evidence_validate
from app.nodes.final_judge import final_judge
from app.nodes.issue_classify import issue_classify
from app.nodes.issue_collect import issue_collect
from app.nodes.opportunity_generate import opportunity_generate
from app.nodes.pain_extract import pain_extract
from app.nodes.query_rewrite import expand_query, query_rewrite
from app.nodes.repo_analyze import repo_analyze
from app.nodes.repo_search import repo_search
from app.nodes.report_write import report_write
from app.nodes.topic_cluster import topic_cluster


def _checked_cards_by_id(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    checked: dict[str, dict[str, Any]] = {}
    for card in (state.get("validated_cards") or []) + (state.get("rejected_cards") or []):
        opportunity_id = card.get("opportunity_id")
        if opportunity_id:
            checked[str(opportunity_id)] = card
    return checked


def validation_diagnostics(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return one diagnostic row for every generated opportunity card."""
    checked_by_id = _checked_cards_by_id(state)
    rows: list[dict[str, Any]] = []
    for raw_card in state.get("opportunity_cards") or []:
        opportunity_id = str(raw_card.get("opportunity_id") or "")
        card = checked_by_id.get(opportunity_id, raw_card)
        validation = card.get("validation") or {}
        evidence_ids = card.get("evidence_ids") or []
        evidence_urls = card.get("evidence_urls") or []
        rows.append(
            {
                "opportunity_id": opportunity_id,
                "title": card.get("title", ""),
                "evidence_count": validation.get("evidence_count", len(evidence_ids)),
                "evidence_urls_count": validation.get("evidence_urls_count", len(evidence_urls)),
                "weak_card": bool(card.get("weak_card", False)),
                "validation_status": validation.get("validation_status", "not_checked"),
                "rejection_reasons": validation.get("rejection_reasons", []),
            }
        )
    return rows


def print_validation_diagnostics(state: dict[str, Any]) -> None:
    """Print validation diagnostics as newline-delimited JSON."""
    print("VALIDATION_DIAGNOSTICS")
    for row in validation_diagnostics(state):
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))


def _quality_gate_allows_pain_extract(state: dict[str, Any]) -> bool:
    high_value_count = len(state.get("high_value_issues") or [])
    repo_coverage_count = len(state.get("selected_repos") or [])
    valid_evidence_count = len(state.get("evidence_items") or [])
    iteration_count = state.get("iteration_count") or 0
    if high_value_count >= 30:
        return True
    if repo_coverage_count >= 3 and valid_evidence_count >= 15:
        return True
    return iteration_count >= 2


def run_live_smoke(topic: str) -> dict[str, Any]:
    """Run the graph step-by-step so diagnostics print right after validation."""
    state: dict[str, Any] = {
        "run_id": str(uuid4()),
        "user_query": topic,
        "errors": [],
        "iteration_count": 0,
    }
    state = query_rewrite(state)

    while True:
        state = repo_search(state)
        state = repo_analyze(state)
        state = issue_collect(state)
        state = issue_classify(state)
        if _quality_gate_allows_pain_extract(state):
            break
        state = expand_query(state)

    for node in [
        pain_extract,
        topic_cluster,
        commercial_gap,
        opportunity_generate,
        evidence_validate,
    ]:
        state = node(state)

    print_validation_diagnostics(state)

    for node in [debate, final_judge, report_write]:
        state = node(state)
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a live graph smoke and print validation diagnostics.")
    parser.add_argument("topic", nargs="?", default="RAG evaluation")
    args = parser.parse_args()

    settings = get_settings()
    state = run_live_smoke(args.topic)

    print("LIVE_SMOKE_SUMMARY")
    print(
        json.dumps(
            {
                "topic": args.topic,
                "mock_mode": settings.mock_mode,
                "validation_mode": settings.validation_mode,
                "raw_issues": len(state.get("raw_issues") or []),
                "evidence_items": len(state.get("evidence_items") or []),
                "classified_issues": len(state.get("classified_issues") or []),
                "high_value_issues": len(state.get("high_value_issues") or []),
                "pain_points": len(state.get("pain_points") or []),
                "commercial_gaps": len(state.get("commercial_gaps") or []),
                "opportunity_cards": len(state.get("opportunity_cards") or []),
                "validated_cards": len(state.get("validated_cards") or []),
                "rejected_cards": len(state.get("rejected_cards") or []),
                "agent_reviews": len(state.get("agent_reviews") or []),
                "final_decisions": len(state.get("final_decisions") or []),
                "errors": len(state.get("errors") or []),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    if state.get("errors"):
        print("LIVE_SMOKE_ERRORS")
        for error in state["errors"][:10]:
            print(str(error))


if __name__ == "__main__":
    main()
