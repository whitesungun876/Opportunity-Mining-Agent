"""Mock GitHub repository search skill."""

from __future__ import annotations


def search_repos(topic: str, queries: list[str]) -> list[dict]:
    """Return deterministic mock repos for a topic."""
    slug = topic.lower().replace(" ", "-")
    names = ["eval-lab", "agent-runtime", "prod-observer", "workflow-kit", "enterprise-bridge"]
    return [
        {
            "repo_id": f"repo_{i+1}",
            "full_name": f"mock-org/{slug}-{name}",
            "url": f"https://github.com/mock-org/{slug}-{name}",
            "stars": 4200 - i * 510,
            "open_issues": 80 + i * 12,
            "matched_query": queries[i % len(queries)] if queries else topic,
            "description": f"Mock repository about {topic} and production workflows.",
        }
        for i, name in enumerate(names)
    ]
