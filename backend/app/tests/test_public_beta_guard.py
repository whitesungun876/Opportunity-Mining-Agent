"""Public beta guard API tests."""

from fastapi.testclient import TestClient

from app.api import runs as runs_api
from app.config import get_settings
from app.main import app
from app.tests.test_run_store_create_and_read import _state


def test_public_beta_preflight_requires_invite(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'beta_preflight.db'}")
    monkeypatch.setenv("PUBLIC_BETA_ENABLED", "true")
    monkeypatch.setenv("PUBLIC_BETA_INVITE_CODES", "demo-code")
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.post("/runs/preflight", json={"topic": "RAG evaluation", "dynamic_search": True})

    assert response.status_code == 403
    assert "invite code" in response.text.lower()
    get_settings.cache_clear()


def test_public_beta_run_accepts_valid_invite(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'beta_run.db'}")
    monkeypatch.setenv("PUBLIC_BETA_ENABLED", "true")
    monkeypatch.setenv("PUBLIC_BETA_INVITE_CODES", "demo-code")
    get_settings.cache_clear()
    monkeypatch.setattr(runs_api, "run_graph", lambda topic, initial_state=None: _state())

    client = TestClient(app)
    response = client.post(
        "/runs",
        json={
            "topic": "RAG evaluation",
            "dynamic_search": True,
            "preflight_id": "pf_test",
            "invite_code": "demo-code",
        },
    )

    assert response.status_code == 200
    assert response.json()["run_id"]
    get_settings.cache_clear()
