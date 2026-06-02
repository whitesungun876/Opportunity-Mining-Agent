"""Repository analysis node."""

from __future__ import annotations

from app.graph.state import GraphState


def repo_analyze(state: GraphState) -> GraphState:
    repos = sorted(state.get("searched_repos") or [], key=lambda item: item.get("stars", 0), reverse=True)
    selected = [
        {
            **repo,
            "selection_reason": "high stars, active issues, and topic match",
            "commercial_signal": "production teams likely need hosted workflows",
        }
        for repo in repos[:5]
    ]
    return {**state, "selected_repos": selected}
