"""Skill wrapper for issue classification."""

from __future__ import annotations

from app.nodes.issue_classify import classify_issue


def classify_issues(issues: list[dict]) -> list[dict]:
    return [classify_issue(issue) for issue in issues]
