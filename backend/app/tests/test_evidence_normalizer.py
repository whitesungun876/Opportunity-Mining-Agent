"""Evidence normalizer tests."""

from app.services.evidence_normalizer import normalize_github_issue


def test_normalize_github_issue_schema_fields():
    issue = {
        "issue_id": "ISSUE_node_1",
        "repo": "owner/repo",
        "repo_id": "repo_1",
        "repo_url": "https://github.com/owner/repo",
        "url": "https://github.com/owner/repo/issues/12",
        "title": "Need production observability",
        "body": "We cannot debug this at scale.",
        "comments": [{"body": "same problem"}],
        "labels": ["observability", "production"],
        "author_login": "octocat",
        "comments_count": 4,
        "reaction_count": 2,
        "state": "OPEN",
        "created_at": "2026-01-01T00:00:00Z",
    }

    evidence = normalize_github_issue(issue, run_id="run_1", is_mock=True)

    assert evidence["source_url"] == "https://github.com/owner/repo/issues/12"
    assert evidence["repo_url"] == "https://github.com/owner/repo"
    assert evidence["author_login"] == "octocat"
    assert evidence["is_mock"] is True
    assert evidence["repo_owner"] == "owner"
    assert evidence["repo_name"] == "repo"
    assert evidence["text_hash"]


def test_normalize_github_issue_accepts_graphql_connections():
    issue = {
        "id": "I_123",
        "repo": "owner/repo",
        "url": "https://github.com/owner/repo/issues/34",
        "title": "Architecture discussion for hosted evaluation",
        "bodyText": "Teams need a managed workflow.",
        "author": {"login": "maintainer"},
        "labels": {"nodes": [{"name": "discussion"}]},
        "comments": {"totalCount": 9, "nodes": [{"bodyText": "Need this too"}]},
        "reactions": {"totalCount": 5},
        "createdAt": "2026-01-02T00:00:00Z",
    }

    evidence = normalize_github_issue(issue, run_id="run_2")

    assert evidence["evidence_id"] == "I_123"
    assert evidence["author_login"] == "maintainer"
    assert evidence["labels"] == ["discussion"]
    assert evidence["comment_count"] == 9
    assert evidence["reaction_count"] == 5
    assert evidence["is_mock"] is False
