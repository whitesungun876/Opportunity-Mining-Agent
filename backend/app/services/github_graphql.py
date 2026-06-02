"""GitHub GraphQL client and data-access helpers.

This module contains the GitHub-specific API details so graph nodes can stay
focused on state transitions. The client is synchronous because the current
LangGraph skeleton runs nodes synchronously.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import time
from typing import Any

import httpx


DEFAULT_GRAPHQL_URL = "https://api.github.com/graphql"


class GitHubGraphQLError(RuntimeError):
    """Raised when GitHub GraphQL execution fails."""


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _rate_limit_from(headers: httpx.Headers, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    data_rate = (payload.get("data") or {}).get("rateLimit") or {}
    return {
        "limit": headers.get("x-ratelimit-limit"),
        "remaining": headers.get("x-ratelimit-remaining") or data_rate.get("remaining"),
        "used": headers.get("x-ratelimit-used"),
        "reset": headers.get("x-ratelimit-reset") or data_rate.get("resetAt"),
        "resource": headers.get("x-ratelimit-resource"),
        "cost": data_rate.get("cost"),
    }


def _split_full_name(full_name: str) -> tuple[str, str]:
    owner, name = full_name.split("/", 1)
    return owner, name


class GitHubGraphQLClient:
    """Small GitHub GraphQL client with retry, pagination, and rate metadata."""

    def __init__(
        self,
        *,
        token: str | None = None,
        endpoint: str | None = None,
        mock_mode: bool | None = None,
        timeout_seconds: float = 20.0,
        retry_limit: int = 2,
        backoff_seconds: float = 1.0,
    ) -> None:
        self.token = token if token is not None else os.getenv("GITHUB_TOKEN")
        self.endpoint = endpoint or os.getenv("GITHUB_GRAPHQL_URL", DEFAULT_GRAPHQL_URL)
        self.mock_mode = _env_bool("MOCK_MODE", True) if mock_mode is None else mock_mode
        self.timeout_seconds = timeout_seconds
        self.retry_limit = retry_limit
        self.backoff_seconds = backoff_seconds
        self.last_rate_limit: dict[str, Any] = {}

    def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        *,
        operation_name: str | None = None,
    ) -> dict[str, Any]:
        """Execute one GraphQL operation and return data plus rate-limit metadata."""
        if self.mock_mode:
            return {"data": {}, "errors": [], "rate_limit": {}, "mock": True}
        if not self.token:
            raise GitHubGraphQLError("GITHUB_TOKEN is required when MOCK_MODE=false")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }
        payload: dict[str, Any] = {"query": query, "variables": variables or {}}
        if operation_name:
            payload["operationName"] = operation_name

        last_error: Exception | None = None
        for attempt in range(self.retry_limit + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(self.endpoint, json=payload, headers=headers)
                rate_limit = _rate_limit_from(response.headers)
                self.last_rate_limit = rate_limit

                if response.status_code in {429, 500, 502, 503, 504} and attempt < self.retry_limit:
                    time.sleep(self.backoff_seconds * (attempt + 1))
                    continue
                response.raise_for_status()

                body = response.json()
                rate_limit = _rate_limit_from(response.headers, body)
                self.last_rate_limit = rate_limit
                errors = body.get("errors") or []
                if errors:
                    message = "; ".join(str(err.get("message", err)) for err in errors[:3])
                    raise GitHubGraphQLError(message)
                return {"data": body.get("data") or {}, "errors": [], "rate_limit": rate_limit, "mock": False}
            except (httpx.HTTPError, ValueError, GitHubGraphQLError) as exc:
                last_error = exc
                if attempt < self.retry_limit:
                    time.sleep(self.backoff_seconds * (attempt + 1))
                    continue
                break
        raise GitHubGraphQLError(str(last_error))

    def paginate_connection(
        self,
        query: str,
        variables: dict[str, Any],
        *,
        connection_path: list[str],
        node_key: str = "nodes",
        page_size: int = 25,
        max_pages: int = 2,
        operation_name: str | None = None,
    ) -> tuple[list[dict], dict[str, Any]]:
        """Collect nodes from a GraphQL connection path using cursor pagination."""
        items: list[dict] = []
        cursor: str | None = variables.get("after")
        rate_limit: dict[str, Any] = {}
        for _ in range(max_pages):
            page_variables = {**variables, "first": page_size, "after": cursor}
            result = self.execute(query, page_variables, operation_name=operation_name)
            rate_limit = result.get("rate_limit") or {}
            connection: Any = result.get("data") or {}
            for key in connection_path:
                connection = (connection or {}).get(key)
            if not connection:
                break
            page_nodes = [node for node in (connection.get(node_key) or []) if node]
            items.extend(page_nodes)
            page_info = connection.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
            if not cursor:
                break
        return items, rate_limit

    def search_repositories(
        self,
        topic: str,
        queries: list[str],
        *,
        per_query: int = 10,
        max_repos: int = 10,
    ) -> list[dict]:
        """Search repositories with shallow metadata only."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).date().isoformat()
        search_terms = list(dict.fromkeys(queries or [topic]))
        graphql = """
        query SearchRepositories($query: String!, $first: Int!, $after: String) {
          rateLimit { cost remaining resetAt }
          search(query: $query, type: REPOSITORY, first: $first, after: $after) {
            pageInfo { hasNextPage endCursor }
            nodes {
              ... on Repository {
                id
                name
                nameWithOwner
                owner { login }
                url
                description
                stargazerCount
                forkCount
                isArchived
                isFork
                hasIssuesEnabled
                pushedAt
                primaryLanguage { name }
                issues(states: OPEN) { totalCount }
              }
            }
          }
        }
        """
        repos_by_name: dict[str, dict] = {}
        for term in search_terms:
            query_text = f"{term} in:name,description,readme stars:>20 archived:false fork:false pushed:>{cutoff}"
            nodes, _ = self.paginate_connection(
                graphql,
                {"query": query_text},
                connection_path=["search"],
                page_size=per_query,
                max_pages=1,
                operation_name="SearchRepositories",
            )
            for node in nodes:
                if node.get("isArchived") or node.get("isFork") or not node.get("hasIssuesEnabled"):
                    continue
                full_name = node.get("nameWithOwner")
                if not full_name:
                    continue
                repos_by_name[full_name] = {
                    "repo_id": node.get("id"),
                    "full_name": full_name,
                    "owner": (node.get("owner") or {}).get("login"),
                    "name": node.get("name"),
                    "url": node.get("url"),
                    "description": node.get("description") or "",
                    "stars": node.get("stargazerCount") or 0,
                    "forks": node.get("forkCount") or 0,
                    "open_issues": ((node.get("issues") or {}).get("totalCount") or 0),
                    "pushed_at": node.get("pushedAt"),
                    "language": (node.get("primaryLanguage") or {}).get("name"),
                    "matched_query": term,
                    "is_mock": False,
                }
        return sorted(repos_by_name.values(), key=lambda repo: repo.get("stars", 0), reverse=True)[:max_repos]

    def search_issues(
        self,
        queries: list[str],
        *,
        per_query: int = 10,
        max_issues: int = 40,
        comment_preview_limit: int = 3,
    ) -> list[dict]:
        """Search GitHub issues globally with shallow issue/comment metadata."""
        graphql = """
        query SearchIssues($query: String!, $first: Int!, $commentPreviewLimit: Int!) {
          rateLimit { cost remaining resetAt }
          search(query: $query, type: ISSUE, first: $first) {
            nodes {
              ... on Issue {
                id
                number
                title
                bodyText
                url
                state
                createdAt
                updatedAt
                author { login }
                repository {
                  id
                  name
                  nameWithOwner
                  owner { login }
                  url
                }
                labels(first: 10) { nodes { name } }
                comments(first: $commentPreviewLimit) {
                  totalCount
                  nodes {
                    id
                    url
                    bodyText
                    createdAt
                    author { login }
                    reactions { totalCount }
                  }
                }
                reactions { totalCount }
              }
            }
          }
        }
        """
        issues_by_url: dict[str, dict] = {}
        for query_text in list(dict.fromkeys(queries)) or []:
            result = self.execute(
                graphql,
                {
                    "query": query_text,
                    "first": per_query,
                    "commentPreviewLimit": comment_preview_limit,
                },
                operation_name="SearchIssues",
            )
            nodes = (((result.get("data") or {}).get("search") or {}).get("nodes") or [])
            for node in nodes:
                if not node:
                    continue
                issue = self._issue_from_search_node(node)
                if issue.get("url"):
                    issues_by_url[issue["url"]] = issue
        return list(issues_by_url.values())[:max_issues]

    def _issue_from_search_node(self, node: dict) -> dict:
        repo = node.get("repository") or {}
        comments = node.get("comments") or {}
        return {
            "issue_id": node.get("id"),
            "number": node.get("number"),
            "title": node.get("title") or "",
            "body": node.get("bodyText") or "",
            "url": node.get("url"),
            "state": node.get("state"),
            "created_at": node.get("createdAt"),
            "updated_at": node.get("updatedAt"),
            "author_login": (node.get("author") or {}).get("login"),
            "labels": [item.get("name") for item in ((node.get("labels") or {}).get("nodes") or []) if item],
            "comments": [
                {
                    "comment_id": comment.get("id"),
                    "source_url": comment.get("url"),
                    "body": comment.get("bodyText") or "",
                    "author_login": (comment.get("author") or {}).get("login"),
                    "created_at": comment.get("createdAt"),
                    "reaction_count": ((comment.get("reactions") or {}).get("totalCount") or 0),
                }
                for comment in (comments.get("nodes") or [])
                if comment
            ],
            "comments_count": comments.get("totalCount") or 0,
            "reaction_count": ((node.get("reactions") or {}).get("totalCount") or 0),
            "repo_id": repo.get("id"),
            "repo": repo.get("nameWithOwner"),
            "repo_owner": (repo.get("owner") or {}).get("login"),
            "repo_name": repo.get("name"),
            "repo_url": repo.get("url"),
            "is_mock": False,
        }

    def collect_issues_for_repo(
        self,
        repo: dict,
        *,
        recent_limit: int = 15,
        high_comment_limit: int = 15,
        comment_preview_limit: int = 3,
    ) -> list[dict]:
        """Collect recent and high-comment issues for one repository."""
        owner = repo.get("owner")
        name = repo.get("name")
        if not owner or not name:
            owner, name = _split_full_name(repo["full_name"])

        recent = self._fetch_issues(
            owner=owner,
            name=name,
            order_field="UPDATED_AT",
            limit=recent_limit,
            comment_preview_limit=comment_preview_limit,
        )
        high_comment = self._fetch_issues(
            owner=owner,
            name=name,
            order_field="COMMENTS",
            limit=high_comment_limit,
            comment_preview_limit=comment_preview_limit,
        )
        merged: dict[str, dict] = {}
        for issue in recent + high_comment:
            issue["repo_id"] = repo.get("repo_id")
            issue["repo"] = repo.get("full_name")
            issue["repo_owner"] = owner
            issue["repo_name"] = name
            issue["repo_url"] = repo.get("url") or f"https://github.com/{owner}/{name}"
            issue["is_mock"] = False
            merged[issue["url"]] = issue
        return list(merged.values())

    def _fetch_issues(
        self,
        *,
        owner: str,
        name: str,
        order_field: str,
        limit: int,
        comment_preview_limit: int,
    ) -> list[dict]:
        graphql = """
        query RepositoryIssues(
          $owner: String!,
          $name: String!,
          $first: Int!,
          $after: String,
          $orderField: IssueOrderField!,
          $commentPreviewLimit: Int!
        ) {
          rateLimit { cost remaining resetAt }
          repository(owner: $owner, name: $name) {
            issues(
              first: $first,
              after: $after,
              states: OPEN,
              orderBy: { field: $orderField, direction: DESC }
            ) {
              pageInfo { hasNextPage endCursor }
              nodes {
                id
                number
                title
                bodyText
                url
                state
                createdAt
                updatedAt
                author { login }
                labels(first: 10) { nodes { name } }
                comments(first: $commentPreviewLimit) {
                  totalCount
                  nodes {
                    id
                    url
                    bodyText
                    createdAt
                    author { login }
                    reactions { totalCount }
                  }
                }
                reactions { totalCount }
              }
            }
          }
        }
        """
        nodes, _ = self.paginate_connection(
            graphql,
            {
                "owner": owner,
                "name": name,
                "orderField": order_field,
                "commentPreviewLimit": comment_preview_limit,
            },
            connection_path=["repository", "issues"],
            page_size=limit,
            max_pages=1,
            operation_name="RepositoryIssues",
        )
        issues: list[dict] = []
        for node in nodes:
            comments = node.get("comments") or {}
            issues.append(
                {
                    "issue_id": node.get("id"),
                    "number": node.get("number"),
                    "title": node.get("title") or "",
                    "body": node.get("bodyText") or "",
                    "url": node.get("url"),
                    "state": node.get("state"),
                    "created_at": node.get("createdAt"),
                    "updated_at": node.get("updatedAt"),
                    "author_login": (node.get("author") or {}).get("login"),
                    "labels": [item.get("name") for item in ((node.get("labels") or {}).get("nodes") or []) if item],
                    "comments": [
                        {
                            "comment_id": comment.get("id"),
                            "source_url": comment.get("url"),
                            "body": comment.get("bodyText") or "",
                            "author_login": (comment.get("author") or {}).get("login"),
                            "created_at": comment.get("createdAt"),
                            "reaction_count": ((comment.get("reactions") or {}).get("totalCount") or 0),
                        }
                        for comment in (comments.get("nodes") or [])
                        if comment
                    ],
                    "comments_count": comments.get("totalCount") or 0,
                    "reaction_count": ((node.get("reactions") or {}).get("totalCount") or 0),
                }
            )
        return issues
