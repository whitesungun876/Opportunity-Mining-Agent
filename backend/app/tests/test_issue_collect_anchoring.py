"""Issue collection anchoring and global-noise guards."""

from app.nodes.issue_collect import _is_generated_digest_issue, rank_issues_for_plan


def _issue(url: str, repo: str, *, comments: int, source: str) -> dict:
    owner, name = repo.split("/", 1)
    return {
        "url": url,
        "repo": repo,
        "repo_owner": owner,
        "repo_name": name,
        "title": "production deployment workflow permission debugging",
        "body": "teams need integration workflow support for production usage",
        "comments_count": comments,
        "reaction_count": 0,
        "state": "OPEN",
        "retrieval_source": source,
        "anchor_repo_match": source == "selected_repo",
    }


def test_rank_issues_prefers_selected_repo_evidence_over_global_drift():
    plan = {
        "positive_signals": ["production", "deployment", "workflow", "permission", "integration"],
        "negative_signals": [],
    }
    selected_repos = [{"full_name": "owner/anchored", "owner": "owner", "name": "anchored"}]
    anchored = _issue("https://github.com/owner/anchored/issues/1", "owner/anchored", comments=3, source="selected_repo")
    drifting_global = _issue(
        "https://github.com/other/drift/issues/99",
        "other/drift",
        comments=20,
        source="global_issue_search",
    )

    ranked = rank_issues_for_plan([drifting_global, anchored], plan, selected_repos)

    assert ranked[0]["url"] == anchored["url"]


def test_generated_digest_issue_is_filtered_as_noise():
    assert _is_generated_digest_issue(
        {
            "title": "Open-source ecosystem digest",
            "body": "Automated digest of popular repositories.",
            "author_login": "github-actions",
        }
    )
