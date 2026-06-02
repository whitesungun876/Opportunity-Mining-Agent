"""Mock GitHub discussion collection skill."""

from __future__ import annotations


def collect_discussions(repos: list[dict]) -> list[dict]:
    """Return lightweight discussion placeholders."""
    return [
        {
            "discussion_id": f"disc_{idx+1}",
            "repo": repo["full_name"],
            "url": f"{repo['url']}/discussions/{idx+1}",
            "title": "How are teams running this in production?",
            "body": "Discussion mentions deployment, monitoring, and security workflow gaps.",
        }
        for idx, repo in enumerate(repos)
    ]
