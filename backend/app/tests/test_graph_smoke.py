"""Main graph smoke test."""

from app.graph.main_graph import run_graph
from app.config import get_settings


def test_graph_smoke_rag_evaluation(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "true")
    get_settings.cache_clear()
    state = run_graph("RAG evaluation")

    cards = state.get("opportunity_cards") or []
    validated = state.get("validated_cards") or []

    assert len(cards) >= 3
    assert len(validated) >= 3
    for card in validated:
        assert len(card.get("evidence_ids", [])) >= 3
        assert len(card.get("evidence_urls", [])) >= 3
        assert all("https://github.com/" in url for url in card["evidence_urls"])

    assert state.get("report_markdown")
    assert "GitHub Opportunity Miner Report" in state["report_markdown"]
    assert state.get("node_latency_summary")
    assert any(item.get("node_name") == "report_write" for item in state["node_latency_summary"])
    get_settings.cache_clear()
