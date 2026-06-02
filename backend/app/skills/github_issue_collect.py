"""Mock GitHub issue collection skill."""

from __future__ import annotations


HIGH_VALUE_TEMPLATES = [
    ("Production deployments lack evaluation gates", "performance issue at scale"),
    ("Need observability for failing retrieval traces", "observability/evaluation/debugging gap"),
    ("Enterprise permission model blocks adoption", "enterprise/security/permission need"),
    ("Integrating with existing CI workflow is painful", "integration challenge"),
    ("Architecture discussion: hosted eval service vs local SDK", "architecture discussion"),
    ("Missing workflow for regression datasets", "missing production workflow feature"),
    ("Latency spikes at scale when replaying traces", "performance issue at scale"),
]

LOW_VALUE_TEMPLATES = [
    ("pip install fails on my laptop", "simple install error"),
    ("it doesn't work", "vague it doesn't work"),
    ("duplicate: how to set env var", "duplicate support request"),
]


def collect_issues(repos: list[dict]) -> list[dict]:
    """Return deterministic high/low-value issues with GitHub-like URLs."""
    issues: list[dict] = []
    counter = 1
    for repo in repos:
        repo_url = repo["url"]
        for title, label in HIGH_VALUE_TEMPLATES:
            issues.append(
                {
                    "issue_id": f"iss_{counter}",
                    "repo": repo["full_name"],
                    "repo_url": repo_url,
                    "url": f"{repo_url}/issues/{counter}",
                    "title": title,
                    "body": f"{title}. Teams report this is blocking production use for {repo['full_name']}.",
                    "labels": [label],
                    "comments_count": 8 + counter % 5,
                }
            )
            counter += 1
        for title, label in LOW_VALUE_TEMPLATES:
            issues.append(
                {
                    "issue_id": f"iss_{counter}",
                    "repo": repo["full_name"],
                    "repo_url": repo_url,
                    "url": f"{repo_url}/issues/{counter}",
                    "title": title,
                    "body": f"{title}. Local setup details are incomplete.",
                    "labels": [label],
                    "comments_count": 1,
                }
            )
            counter += 1
    return issues
