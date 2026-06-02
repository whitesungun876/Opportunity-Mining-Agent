"""Issue collection node."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.config import get_settings
from app.graph.state import GraphState
from app.harness.tool_runner import ToolRunner
from app.search.scorer import score_issue_for_plan
from app.services.evidence_normalizer import normalize_github_issue
from app.services.github_graphql import GitHubGraphQLClient
from app.skills.github_issue_collect import collect_issues


GLOBAL_ISSUE_MAX_SHARE = 0.4
SELECTED_REPO_SCORE_BOOST = 12.0
GLOBAL_ONLY_SCORE_PENALTY = 6.0


def _repo_key(value: dict[str, Any]) -> str:
    full_name = value.get("repo") or value.get("full_name")
    if full_name and "/" in str(full_name):
        return str(full_name).lower()
    owner = value.get("repo_owner") or value.get("owner")
    name = value.get("repo_name") or value.get("name")
    if owner and name:
        return f"{owner}/{name}".lower()
    return ""


def _selected_repo_keys(repos: list[dict]) -> set[str]:
    return {key for key in (_repo_key(repo) for repo in repos) if key}


def _is_generated_digest_issue(issue: dict[str, Any]) -> bool:
    text = " ".join(
        [
            str(issue.get("title") or ""),
            str(issue.get("body") or ""),
            str(issue.get("author_login") or ""),
        ]
    ).lower()
    generated_markers = [
        "ecosystem digest",
        "weekly digest",
        "daily digest",
        "generated digest",
        "automated digest",
        "github-actions",
    ]
    return any(marker in text for marker in generated_markers)


def _annotate_issue(issue: dict[str, Any], *, source: str, selected_repos: set[str]) -> dict[str, Any]:
    repo_key = _repo_key(issue)
    return {
        **issue,
        "retrieval_source": source,
        "anchor_repo_match": bool(repo_key and repo_key in selected_repos),
    }


def _anchored_issue_score(issue: dict[str, Any], search_plan: dict, selected_repos: set[str]) -> float:
    score = float(score_issue_for_plan(issue, search_plan))
    repo_key = _repo_key(issue)
    if repo_key and repo_key in selected_repos:
        score += SELECTED_REPO_SCORE_BOOST
    elif issue.get("retrieval_source") == "global_issue_search":
        score -= GLOBAL_ONLY_SCORE_PENALTY
    if _is_generated_digest_issue(issue):
        score -= 25.0
    return score


def rank_issues_for_plan(issues: list[dict], search_plan: dict, selected_repos: list[dict]) -> list[dict]:
    selected_keys = _selected_repo_keys(selected_repos)
    deduped = {issue["url"]: issue for issue in issues if issue.get("url")}
    return sorted(
        deduped.values(),
        key=lambda issue: _anchored_issue_score(issue, search_plan, selected_keys),
        reverse=True,
    )


def _global_issue_budget(max_issues: int, repo_issue_count: int, global_query_count: int) -> tuple[int, int]:
    if global_query_count <= 0:
        return 0, 0
    max_global = max(5, int(max_issues * GLOBAL_ISSUE_MAX_SHARE))
    remaining = max(0, max_issues - repo_issue_count)
    # Keep global search as a discovery/backup layer. If selected repos already
    # supplied evidence, use only the smaller leftover budget.
    budget = min(max_global, remaining if repo_issue_count else max_global)
    if budget <= 0:
        budget = min(max(3, max_issues // 5), max_global)
    per_query = max(2, min(8, budget // max(1, global_query_count)))
    return budget, per_query


def _normalize_issues(state: GraphState, issues: list[dict], *, is_mock: bool) -> list[dict]:
    run_id = state.get("run_id", "local")
    return [normalize_github_issue(issue, run_id=run_id, is_mock=is_mock) for issue in issues]


def issue_collect(state: GraphState) -> GraphState:
    settings = get_settings()
    errors = list(state.get("errors") or [])

    if settings.mock_mode:
        issues = collect_issues(state.get("selected_repos") or [])
        evidence_items = _normalize_issues(state, issues, is_mock=True)
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
        repos = state.get("selected_repos") or []
        selected_repo_keys = _selected_repo_keys(repos)

        def collect_repo(repo: dict) -> tuple[dict, list[dict], list[str]]:
            result = runner.run(
                client.collect_issues_for_repo,
                repo,
                node_name="github_issue_collect",
                timeout_seconds=35,
                retry_limit=2,
                allow_partial_failure=True,
            )
            if isinstance(result, dict) and result.get("partial_failure"):
                repo_name = repo.get("full_name", "unknown")
                return repo, [], [f"{repo_name}: {err}" for err in result.get("errors") or []]
            return repo, result or [], []

        repo_results: list[tuple[dict, list[dict], list[str]]] = []
        if len(repos) <= 1 or settings.max_github_concurrency <= 1:
            repo_results = [collect_repo(repo) for repo in repos]
        else:
            max_workers = min(settings.max_github_concurrency, len(repos))
            ordered_results: list[tuple[dict, list[dict], list[str]] | None] = [None] * len(repos)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(collect_repo, repo): idx for idx, repo in enumerate(repos)}
                for future in as_completed(futures):
                    ordered_results[futures[future]] = future.result()
            repo_results = [item for item in ordered_results if item is not None]

        issues = []
        evidence_items = []
        for repo, repo_issues, repo_errors in repo_results:
            errors.extend(repo_errors)
            repo_issues = [
                _annotate_issue(issue, source="selected_repo", selected_repos=selected_repo_keys)
                for issue in repo_issues
                if not _is_generated_digest_issue(issue)
            ]
            issues.extend(repo_issues)
            evidence_items.extend(
                normalize_github_issue(issue, run_id=state.get("run_id", "local"), repo=repo, is_mock=False)
                for issue in repo_issues
            )

        search_plan = state.get("search_plan") or {}
        global_queries = state.get("global_issue_queries") or search_plan.get("global_issue_queries") or []
        if global_queries:
            max_issues = int(search_plan.get("max_issues") or 80)
            global_budget, per_query = _global_issue_budget(max_issues, len(issues), len(global_queries))
            per_query = int(state.get("benchmark_per_query") or per_query)
            result = runner.run(
                client.search_issues,
                global_queries,
                node_name="github_global_issue_search",
                timeout_seconds=45,
                retry_limit=2,
                allow_partial_failure=True,
                per_query=per_query,
                max_issues=global_budget,
            )
            if isinstance(result, dict) and result.get("partial_failure"):
                errors.extend(result.get("errors") or [])
            else:
                global_issues = [
                    _annotate_issue(issue, source="global_issue_search", selected_repos=selected_repo_keys)
                    for issue in (result or [])
                    if not _is_generated_digest_issue(issue)
                ]
                issues.extend(global_issues)
                evidence_items.extend(
                    normalize_github_issue(issue, run_id=state.get("run_id", "local"), is_mock=False)
                    for issue in global_issues
                )

        if state.get("search_plan"):
            issues = rank_issues_for_plan(
                issues,
                state.get("search_plan") or {},
                state.get("selected_repos") or [],
            )[: int((state.get("search_plan") or {}).get("max_issues") or 80)]
            issue_urls = [issue.get("url") for issue in issues if issue.get("url")]
            issue_url_order = {url: idx for idx, url in enumerate(issue_urls)}
            evidence_items = [
                item
                for item in evidence_items
                if item.get("source_url") in issue_url_order
            ]
            evidence_items.sort(key=lambda item: issue_url_order.get(item.get("source_url"), len(issue_url_order)))

    existing = state.get("raw_issues") or []
    merged = {issue["url"]: issue for issue in existing + issues}
    existing_evidence = state.get("evidence_items") or []
    evidence_merged = {item["source_url"]: item for item in existing_evidence + evidence_items}
    return {
        **state,
        "raw_issues": list(merged.values()),
        "evidence_items": list(evidence_merged.values()),
        "errors": errors,
    }
