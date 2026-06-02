"""Evidence quality ranking for dynamic search results."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.search.templates import (
    ENTERPRISE_SIGNALS,
    INTEGRATION_SIGNALS,
    OBSERVABILITY_SIGNALS,
    PRODUCTION_SIGNALS,
)


def _text(item: dict[str, Any]) -> str:
    comments = item.get("comments") or []
    comment_text = " ".join(str(comment.get("body") or "") for comment in comments if isinstance(comment, dict))
    return " ".join(
        [
            str(item.get("title") or ""),
            str(item.get("body") or ""),
            " ".join(str(label) for label in item.get("labels") or []),
            comment_text,
        ]
    ).lower()


def _count(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _recent_score(item: dict[str, Any]) -> float:
    raw = item.get("updated_at") or item.get("created_at") or item.get("collected_at")
    if not raw:
        return 0.0
    try:
        normalized = str(raw).replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.0
    age_days = (datetime.now(timezone.utc) - dt).days
    if age_days <= 90:
        return 1.0
    if age_days <= 365:
        return 0.5
    return 0.0


class EvidenceQualityRanker:
    """Score evidence by production/commercial usefulness."""

    def __init__(self, search_plan: dict[str, Any]) -> None:
        self.search_plan = search_plan
        self.positive_signals = [str(item).lower() for item in search_plan.get("positive_signals", [])]
        self.negative_signals = [str(item).lower() for item in search_plan.get("negative_signals", [])]

    def rank(self, evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        repo_counts: dict[str, int] = {}
        for item in evidence_items:
            repo = self._repo_key(item)
            repo_counts[repo] = repo_counts.get(repo, 0) + 1
        scored = [self.score(item, repo_counts) for item in evidence_items]
        return sorted(scored, key=lambda item: item.get("evidence_quality_score", 0), reverse=True)

    def score(self, item: dict[str, Any], repo_counts: dict[str, int] | None = None) -> dict[str, Any]:
        repo_counts = repo_counts or {}
        text = _text(item)
        matched_positive = [signal for signal in self.positive_signals if signal and signal in text]
        matched_negative = [signal for signal in self.negative_signals if signal and signal in text]
        signal_groups = {
            "production": [signal for signal in PRODUCTION_SIGNALS if signal in text],
            "integration": [signal for signal in INTEGRATION_SIGNALS if signal in text],
            "enterprise": [signal for signal in ENTERPRISE_SIGNALS if signal in text],
            "observability": [signal for signal in OBSERVABILITY_SIGNALS if signal in text],
        }
        comment_score = min(_count(item.get("comment_count", item.get("comments_count"))), 12) * 0.8
        reaction_score = min(_count(item.get("reaction_count")), 20) * 0.25
        repo_key = self._repo_key(item)
        repo_diversity_bonus = 2.0 if repo_counts.get(repo_key, 0) <= 3 else 0.5
        state_bonus = 1.5 if str(item.get("state") or "").upper() == "OPEN" else 0.2
        recent_bonus = _recent_score(item)
        group_bonus = sum(2.0 for signals in signal_groups.values() if signals)
        anchor_bonus = 3.0 if item.get("anchor_repo_match") or item.get("retrieval_source") == "selected_repo" else 0.0
        global_penalty = 2.0 if item.get("retrieval_source") == "global_issue_search" and not item.get("anchor_repo_match") else 0.0
        score = (
            len(matched_positive) * 2.0
            - len(matched_negative) * 2.5
            + comment_score
            + reaction_score
            + repo_diversity_bonus
            + state_bonus
            + recent_bonus
            + group_bonus
            + anchor_bonus
            - global_penalty
        )
        matched_signals = sorted(set(matched_positive + [signal for signals in signal_groups.values() for signal in signals]))
        return {
            **item,
            "evidence_quality_score": round(max(0.0, score), 3),
            "matched_signals": matched_signals,
            "rank_reason": (
                f"matched={len(matched_signals)}, comments={_count(item.get('comment_count', item.get('comments_count')))}, "
                f"reactions={_count(item.get('reaction_count'))}, negatives={len(matched_negative)}"
            ),
        }

    def _repo_key(self, item: dict[str, Any]) -> str:
        return str(item.get("repo") or f"{item.get('repo_owner')}/{item.get('repo_name')}")


def score_issue_for_plan(issue: dict, search_plan: dict) -> float:
    """Backwards-compatible score helper for raw issue payloads."""
    return EvidenceQualityRanker(search_plan).score(issue).get("evidence_quality_score", 0.0)
