"""Pain points must reference known evidence ids."""

from app.graph.main_graph import run_graph


def test_pain_points_have_existing_evidence_ids():
    state = run_graph("RAG evaluation")

    evidence_ids = {item["evidence_id"] for item in state.get("evidence_items") or []}
    assert evidence_ids

    for pain in state.get("pain_points") or []:
        assert pain.get("evidence_id") in evidence_ids
