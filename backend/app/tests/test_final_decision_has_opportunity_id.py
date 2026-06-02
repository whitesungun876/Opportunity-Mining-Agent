"""Final decisions should bind to opportunity ids."""

from app.graph.main_graph import run_graph


def test_final_decision_has_opportunity_id():
    state = run_graph("RAG evaluation")

    validated_ids = {card["opportunity_id"] for card in state.get("validated_cards") or []}
    decision_ids = {decision.get("opportunity_id") for decision in state.get("final_decisions") or []}

    assert validated_ids
    assert validated_ids == decision_ids
    assert len(state.get("validated_cards") or []) == len(state.get("final_decisions") or [])
    for decision in state.get("final_decisions") or []:
        assert decision.get("decision") in {"build", "validate", "watch", "reject"}
