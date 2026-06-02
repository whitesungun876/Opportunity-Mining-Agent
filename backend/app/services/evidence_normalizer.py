"""Normalize GitHub sources into a single evidence schema."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any


def _text_hash(*parts: str) -> str:
    text = "\n".join(part for part in parts if part)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _repo_parts(payload: dict[str, Any]) -> tuple[str, str]:
    owner = payload.get("repo_owner") or payload.get("owner")
    name = payload.get("repo_name") or payload.get("name")
    full_name = payload.get("repo") or payload.get("full_name")
    if (not owner or not name) and full_name and "/" in full_name:
        owner, name = full_name.split("/", 1)
    return owner or "", name or ""


def normalize_github_issue(
    issue: dict[str, Any],
    *,
    run_id: str,
    repo: dict[str, Any] | None = None,
    is_mock: bool = False,
) -> dict[str, Any]:
    """Normalize one GitHub issue-like payload into evidence schema."""
    merged = {**(repo or {}), **issue}
    repo_owner, repo_name = _repo_parts(merged)
    source_url = merged.get("source_url") or merged.get("url") or ""
    repo_url = merged.get("repo_url") or (f"https://github.com/{repo_owner}/{repo_name}" if repo_owner and repo_name else "")
    body = merged.get("body") or merged.get("bodyText") or ""
    title = merged.get("title") or ""
    comments = merged.get("comments") or []
    if isinstance(comments, dict):
        comment_count = comments.get("totalCount", len(comments.get("nodes") or []))
        comments = comments.get("nodes") or []
    elif isinstance(comments, int):
        comment_count = comments
        comments = []
    else:
        comment_count = merged.get("comment_count", merged.get("comments_count", len(comments)))
    reactions = merged.get("reactions") if isinstance(merged.get("reactions"), dict) else {}
    reaction_count = merged.get("reaction_count", merged.get("reactions_count", reactions.get("totalCount", 0)))
    evidence_id = merged.get("evidence_id") or merged.get("issue_id") or merged.get("id") or _text_hash(source_url, title)[:16]
    labels = merged.get("labels") or []
    if isinstance(labels, dict):
        labels = labels.get("nodes") or []
    normalized_labels = [
        label.get("name") if isinstance(label, dict) else str(label)
        for label in labels
        if label
    ]
    return {
        "evidence_id": str(evidence_id),
        "run_id": run_id,
        "repo_id": merged.get("repo_id") or merged.get("repository_id") or "",
        "repo_owner": repo_owner,
        "repo_name": repo_name,
        "repo_url": repo_url,
        "source_type": merged.get("source_type") or "github_issue",
        "source_url": source_url,
        "title": title,
        "body": body,
        "comments": comments,
        "labels": normalized_labels,
        "author_login": merged.get("author_login") or ((merged.get("author") or {}).get("login") if isinstance(merged.get("author"), dict) else ""),
        "comment_count": int(comment_count or 0),
        "reaction_count": int(reaction_count or 0),
        "state": merged.get("state") or "",
        "created_at": merged.get("created_at") or merged.get("createdAt") or "",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "is_mock": bool(is_mock or merged.get("is_mock", False)),
        "text_hash": _text_hash(source_url, title, body),
        "retrieval_source": merged.get("retrieval_source") or "",
        "anchor_repo_match": bool(merged.get("anchor_repo_match", False)),
        "matched_query": merged.get("matched_query") or "",
    }


def normalize_github_evidence(
    payload: dict[str, Any],
    *,
    run_id: str,
    source_type: str = "github_issue",
    repo: dict[str, Any] | None = None,
    is_mock: bool = False,
) -> dict[str, Any]:
    """Normalize a supported GitHub payload type."""
    if source_type in {"github_issue", "issue"}:
        return normalize_github_issue(payload, run_id=run_id, repo=repo, is_mock=is_mock)
    return normalize_github_issue({**payload, "source_type": source_type}, run_id=run_id, repo=repo, is_mock=is_mock)
