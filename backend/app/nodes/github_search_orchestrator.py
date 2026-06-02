"""GitHub search orchestration node.

This keeps GitHub-specific retrieval behind the existing repo/issue nodes while
the product graph works with a SearchPlan.
"""

from __future__ import annotations

from app.graph.state import GraphState
from app.nodes.issue_collect import issue_collect
from app.nodes.repo_analyze import repo_analyze
from app.nodes.repo_search import repo_search


def github_search_orchestrator(state: GraphState) -> GraphState:
    after_repo_search = repo_search(state)
    after_repo_analyze = repo_analyze(after_repo_search)
    after_issue_collect = issue_collect(after_repo_analyze)
    evidence_items = after_issue_collect.get("evidence_items") or []
    return {
        **after_issue_collect,
        "evidence_pool": evidence_items,
    }
