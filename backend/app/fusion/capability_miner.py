"""Deterministic capability discovery from repos and evidence."""

from __future__ import annotations

import re
from typing import Any

from app.fusion.schemas import Capability


CAPABILITY_PATTERNS = [
    {
        "name": "Tracing and observability",
        "keywords": ["trace", "tracing", "observability", "monitoring", "debug", "debugging", "telemetry"],
        "description": "Captures execution traces, metrics, and debugging context for production workflows.",
        "methods": ["trace ingestion", "event timeline", "failure replay"],
    },
    {
        "name": "Evaluation and regression testing",
        "keywords": ["eval", "evaluation", "regression", "benchmark", "quality", "dataset", "metrics"],
        "description": "Compares outputs against datasets, metrics, and release-quality thresholds.",
        "methods": ["regression dataset comparison", "metric scoring", "quality gates"],
    },
    {
        "name": "Enterprise access controls",
        "keywords": ["auth", "sso", "oidc", "permission", "security", "rbac", "audit", "team"],
        "description": "Provides team permissions, authentication, security, and audit workflows.",
        "methods": ["rbac", "sso integration", "audit logging"],
    },
    {
        "name": "Integration and workflow connectors",
        "keywords": ["integration", "api", "sdk", "webhook", "plugin", "connector", "workflow"],
        "description": "Connects the project into existing developer workflows and external systems.",
        "methods": ["sdk", "webhook", "workflow connector"],
    },
    {
        "name": "Managed deployment layer",
        "keywords": ["deploy", "deployment", "self-host", "docker", "kubernetes", "cloud", "scale"],
        "description": "Packages deployment, scaling, and hosted operations around an open-source project.",
        "methods": ["hosted deployment", "container orchestration", "scaling playbook"],
    },
    {
        "name": "Dashboard and review UI",
        "keywords": ["dashboard", "ui", "admin", "review", "report", "no-code"],
        "description": "Turns low-level project signals into reviewable dashboards and team workflows.",
        "methods": ["dashboard", "review queue", "reporting workflow"],
    },
]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:80]


def _repo_key(repo: dict[str, Any]) -> str:
    return str(repo.get("full_name") or repo.get("name_with_owner") or repo.get("repo") or f"{repo.get('owner')}/{repo.get('name')}").strip("/")


def _evidence_repo_key(item: dict[str, Any]) -> str:
    if item.get("repo_owner") or item.get("repo_name"):
        return f"{item.get('repo_owner')}/{item.get('repo_name')}".strip("/")
    repo_url = str(item.get("repo_url") or "")
    if "github.com/" in repo_url:
        return repo_url.split("github.com/", 1)[1].strip("/")
    return str(item.get("repo") or "")


def _text(item: dict[str, Any]) -> str:
    return " ".join(
        [
            str(item.get("title") or ""),
            str(item.get("body") or ""),
            " ".join(str(label) for label in item.get("labels") or []),
            " ".join(str(signal) for signal in item.get("matched_signals") or []),
        ]
    ).lower()


def _maturity(repo: dict[str, Any], evidence_count: int) -> float:
    stars = float(repo.get("stars") or repo.get("stargazerCount") or 0)
    issue_signal = min(evidence_count, 10) * 0.025
    star_signal = min(stars / 5000.0, 0.35)
    baseline = 0.45 if repo.get("is_mock") else 0.55
    return round(min(1.0, baseline + star_signal + issue_signal), 3)


class CapabilityMiner:
    """Mine transferable repo capabilities without adding topic-specific query lists."""

    def mine(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        repos = state.get("selected_repos") or state.get("searched_repos") or []
        evidence_items = state.get("ranked_evidence_items") or state.get("evidence_items") or []
        by_repo: dict[str, list[dict[str, Any]]] = {}
        for item in evidence_items:
            by_repo.setdefault(_evidence_repo_key(item), []).append(item)

        capabilities: list[Capability] = []
        for repo in repos:
            repo_key = _repo_key(repo)
            if not repo_key or repo_key == "None/None":
                continue
            repo_evidence = by_repo.get(repo_key, [])
            repo_text = " ".join([str(repo.get("description") or ""), *[_text(item) for item in repo_evidence]])
            for pattern in CAPABILITY_PATTERNS:
                matched = [keyword for keyword in pattern["keywords"] if keyword in repo_text]
                if not matched:
                    continue
                evidence_ids = [
                    str(item.get("evidence_id"))
                    for item in repo_evidence
                    if item.get("evidence_id") and any(keyword in _text(item) for keyword in pattern["keywords"])
                ][:8]
                clues = [
                    str(item.get("title"))
                    for item in repo_evidence
                    if item.get("title") and item.get("evidence_id") in evidence_ids
                ][:4]
                capabilities.append(
                    Capability(
                        capability_id=f"cap_{_slug(repo_key)}_{_slug(pattern['name'])}",
                        name=pattern["name"],
                        description=pattern["description"],
                        source_repo=repo_key,
                        maturity_score=_maturity(repo, len(repo_evidence)),
                        implementation_clues=clues or matched[:4],
                        related_methods=pattern["methods"],
                        evidence_ids=evidence_ids,
                    )
                )

        deduped: dict[str, Capability] = {}
        for capability in capabilities:
            existing = deduped.get(capability.capability_id)
            if not existing or capability.maturity_score > existing.maturity_score:
                deduped[capability.capability_id] = capability
        return [item.model_dump() for item in sorted(deduped.values(), key=lambda cap: cap.maturity_score, reverse=True)]


def discover_capabilities(state: dict[str, Any]) -> list[dict[str, Any]]:
    return CapabilityMiner().mine(state)
