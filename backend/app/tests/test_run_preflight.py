"""Preflight opportunity-fit tests."""

from fastapi.testclient import TestClient

from app.api import runs as runs_api
from app.config import get_settings
from app.main import app
from app.services.preflight import run_preflight
from app.services.preflight_cache import get_preflight_initial_state


def test_preflight_ambiguous_query_needs_refinement():
    result = run_preflight("agent")

    assert result["preflight_id"]
    assert result["query_scope"] == "ambiguous"
    assert result["opportunity_fit"] == "needs_refinement"
    assert result["should_run"] is False
    assert result["suggested_queries"]


def test_preflight_suggestions_prioritize_commercial_signals():
    result = run_preflight("agent")
    joined = " | ".join(result["suggested_queries"]).lower()

    assert "self-hosted deployment" in joined
    assert "enterprise auth" in joined
    assert "managed hosted" in joined


def test_preflight_medium_signal_can_run(monkeypatch):
    monkeypatch.setattr(
        "app.services.preflight._opportunity_fit",
        lambda scope, evidence_count, strong_count, repo_count: "medium",
    )

    result = run_preflight("RAG evaluation")

    assert result["opportunity_fit"] == "medium"
    assert result["should_run"] is True


def test_preflight_returns_warm_start_state(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "true")
    get_settings.cache_clear()

    result = run_preflight("RAG evaluation")

    warm_state = get_preflight_initial_state(result["preflight_id"])

    assert warm_state is not None
    assert warm_state["warm_start_evidence"] is True
    assert warm_state["search_plan"]
    assert warm_state["evidence_items"]
    get_settings.cache_clear()


def test_preflight_api_contract(monkeypatch):
    monkeypatch.setattr(
        runs_api,
        "run_preflight",
        lambda topic, dynamic_search=True: {
            "topic": topic,
            "preflight_id": "pf_test",
            "normalized_topic": topic,
            "query_scope": "focused",
            "opportunity_fit": "low",
            "should_run": False,
            "reason": "Weak signal.",
            "estimated_cost": "medium",
            "estimated_runtime": "medium",
            "evidence_count": 4,
            "strong_evidence_count": 0,
            "repo_count": 1,
            "suggested_queries": ["RAG evaluation observability"],
            "search_plan": {"query_scope": "focused"},
        },
    )

    client = TestClient(app)
    response = client.post("/runs/preflight", json={"topic": "RAG regression testing", "dynamic_search": True})

    assert response.status_code == 200
    payload = response.json()
    assert payload["opportunity_fit"] == "low"
    assert payload["should_run"] is False
    assert payload["suggested_queries"] == ["RAG evaluation observability"]
