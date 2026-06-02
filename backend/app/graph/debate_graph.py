"""Mock multi-agent debate subgraph."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class DebateState(TypedDict, total=False):
    card: dict
    agent_reviews: list[dict]
    final_decision: dict


def _review(agent: str, score: int, recommendation: str, key_argument: str, main_risk: str) -> dict:
    return {
        "agent": agent,
        "score": score,
        "key_argument": key_argument,
        "main_risk": main_risk,
        "recommendation": recommendation,
    }


def pm_review(state: DebateState) -> DebateState:
    card = state["card"]
    review = _review(
        "PM",
        8,
        "validate",
        f"{card['title']} maps to a repeated workflow pain with clear users.",
        "The initial product scope may become too broad.",
    )
    return {**state, "agent_reviews": (state.get("agent_reviews") or []) + [review]}


def engineer_review(state: DebateState) -> DebateState:
    card = state["card"]
    migration_cost = card.get("migration_cost", "medium")
    score = {"low": 8, "medium": 7, "high": 5}.get(migration_cost, 6)
    review = _review(
        "Engineer",
        score,
        "validate" if score >= 7 else "watch",
        "The MVP can start as a thin hosted layer or plugin around existing repos.",
        "GitHub API limits and repo-specific workflows may complicate automation.",
    )
    return {**state, "agent_reviews": (state.get("agent_reviews") or []) + [review]}


def founder_review(state: DebateState) -> DebateState:
    review = _review(
        "Founder",
        8,
        "validate",
        "Repeated production blockers suggest a wedge for paid teams.",
        "Open-source users may resist paying unless the hosted value is immediate.",
    )
    return {**state, "agent_reviews": (state.get("agent_reviews") or []) + [review]}


def investor_review(state: DebateState) -> DebateState:
    review = _review(
        "Investor",
        7,
        "validate",
        "The category can expand from one repo ecosystem into cross-repo workflow infrastructure.",
        "Market size must be proven beyond early technical adopters.",
    )
    return {**state, "agent_reviews": (state.get("agent_reviews") or []) + [review]}


def skeptic_review(state: DebateState) -> DebateState:
    review = _review(
        "Skeptic",
        6,
        "watch",
        "Some issues may be support noise rather than budget-backed demand.",
        "Evidence needs buyer interviews before build commitment.",
    )
    return {**state, "agent_reviews": (state.get("agent_reviews") or []) + [review]}


def final_judge(state: DebateState) -> DebateState:
    card = state["card"]
    reviews = state.get("agent_reviews") or []
    avg_score = sum(item["score"] for item in reviews) / max(1, len(reviews))
    migration_cost = card.get("migration_cost", "medium")
    if avg_score >= 7.5 and migration_cost in {"low", "medium"}:
        decision = "build"
    elif avg_score >= 6.5:
        decision = "validate"
    elif avg_score >= 5.5:
        decision = "watch"
    else:
        decision = "reject"
    final = {
        "decision": decision,
        "score": int(avg_score * 10),
        "migration_cost": migration_cost,
        "best_product_form": card.get("best_product_form", "Watch"),
        "reason": "Mock debate found repeated evidence and a plausible production workflow wedge.",
        "first_validation_action": "Interview five maintainers or teams who commented on the linked GitHub issues.",
    }
    return {**state, "final_decision": final}


def build_debate_graph():
    graph = StateGraph(DebateState)
    graph.add_node("pm_review", pm_review)
    graph.add_node("engineer_review", engineer_review)
    graph.add_node("founder_review", founder_review)
    graph.add_node("investor_review", investor_review)
    graph.add_node("skeptic_review", skeptic_review)
    graph.add_node("final_judge", final_judge)

    graph.add_edge(START, "pm_review")
    graph.add_edge("pm_review", "engineer_review")
    graph.add_edge("engineer_review", "founder_review")
    graph.add_edge("founder_review", "investor_review")
    graph.add_edge("investor_review", "skeptic_review")
    graph.add_edge("skeptic_review", "final_judge")
    graph.add_edge("final_judge", END)
    return graph.compile()


def run_debate_graph(card: dict) -> dict:
    """Run the debate subgraph for one opportunity card."""
    return build_debate_graph().invoke({"card": card, "agent_reviews": []})
