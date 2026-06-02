"""Skill wrapper for mock pain extraction."""

from __future__ import annotations


def extract_pains(issues: list[dict]) -> list[dict]:
    return [
        {
            "pain_id": f"pain_{idx+1}",
            "issue_id": issue["issue_id"],
            "evidence_id": issue.get("evidence_id") or issue["issue_id"],
            "evidence_ids": [issue.get("evidence_id") or issue["issue_id"]],
            "pain_type": "unclear",
            "complaint": issue["title"],
            "persona": "production engineering team",
            "context": "adopting open-source tooling in a production workflow",
            "cause": issue.get("reason", "production workflow gap"),
            "action_intent": "wants a hosted layer, plugin, or workflow integration",
            "severity": 0.6,
            "workaround": "manual workflow or custom integration",
            "business_signal": "Potential demand for hosted layer, plugin, or workflow integration",
            "supporting_quote": issue["title"],
        }
        for idx, issue in enumerate(issues)
    ]
