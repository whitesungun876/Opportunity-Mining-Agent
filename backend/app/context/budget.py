"""Token budget defaults for context packets."""

DEFAULT_NODE_BUDGETS: dict[str, int] = {
    "query_rewrite": 1200,
    "issue_classify": 3000,
    "pain_extract": 4000,
    "topic_cluster": 3500,
    "commercial_gap": 3000,
    "opportunity_generate": 3500,
    "evidence_validate": 2500,
    "debate": 5000,
}


def budget_for(node_name: str) -> int:
    """Return a conservative per-node token budget."""
    return DEFAULT_NODE_BUDGETS.get(node_name, 2000)
