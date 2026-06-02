"""Repository search node."""

from __future__ import annotations

from app.config import get_settings
from app.graph.state import GraphState
from app.harness.tool_runner import ToolRunner
from app.services.github_graphql import GitHubGraphQLClient
from app.skills.github_repo_search import search_repos


def _select_repos(repos: list[dict], limit: int = 5) -> list[dict]:
    return sorted(repos, key=lambda repo: repo.get("stars", 0), reverse=True)[:limit]


def repo_search(state: GraphState) -> GraphState:
    settings = get_settings()
    errors = list(state.get("errors") or [])
    plan = state.get("search_plan") or {}
    repo_queries = state.get("repo_search_queries") or plan.get("repo_search_queries") or state.get("github_queries") or []
    max_repos = int(plan.get("max_repos") or 5)
    if plan.get("query_scope") == "repo_specific" and plan.get("repo_hints"):
        full_name = str(plan["repo_hints"][0])
        owner, name = full_name.split("/", 1)
        repo = {
            "repo_id": full_name,
            "full_name": full_name,
            "owner": owner,
            "name": name,
            "url": f"https://github.com/{full_name}",
            "description": "Repo-specific opportunity analysis target.",
            "stars": 0,
            "forks": 0,
            "open_issues": 0,
            "is_mock": settings.mock_mode,
            "matched_query": full_name,
        }
        return {
            **state,
            "searched_repos": [repo],
            "selected_repos": [repo],
            "errors": errors,
        }
    if settings.mock_mode:
        repos = search_repos(state.get("canonical_topic", ""), repo_queries)
    else:
        client = GitHubGraphQLClient(
            token=settings.github_token,
            endpoint=settings.github_graphql_url,
            mock_mode=False,
        )
        runner = ToolRunner(
            mock_mode=False,
            trace_logger=state.get("_trace_logger"),  # type: ignore[arg-type]
            run_id=state.get("run_id", "local"),
        )
        result = runner.run(
            client.search_repositories,
            state.get("canonical_topic", ""),
            repo_queries,
            node_name="github_repo_search",
            timeout_seconds=35,
            retry_limit=2,
            max_repos=max_repos,
        )
        if isinstance(result, dict) and result.get("partial_failure"):
            errors.extend(result.get("errors") or [])
            repos = []
        else:
            repos = result or []

    existing = state.get("searched_repos") or []
    merged = {repo["full_name"]: repo for repo in existing + repos}
    searched_repos = list(merged.values())
    return {
        **state,
        "searched_repos": searched_repos,
        "selected_repos": _select_repos(searched_repos, limit=max_repos),
        "errors": errors,
    }
