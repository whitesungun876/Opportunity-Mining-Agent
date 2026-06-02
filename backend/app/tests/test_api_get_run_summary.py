"""FastAPI run summary tests."""

from fastapi.testclient import TestClient
import time

from app.api import runs as runs_api
from app.config import get_settings
from app.main import app
from app.tests.test_run_store_create_and_read import _state


def test_api_get_run_summary(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'api_summary.db'}")
    get_settings.cache_clear()
    monkeypatch.setattr(runs_api, "run_graph", lambda topic, initial_state=None: _state())

    client = TestClient(app)
    run_id = client.post("/runs", json={"topic": "RAG evaluation"}).json()["run_id"]
    for _ in range(20):
        status = client.get(f"/runs/{run_id}/status").json()
        if status["status"] == "completed":
            break
        time.sleep(0.05)
    assert status["status"] == "completed"
    response = client.get(f"/runs/{run_id}/summary")

    assert response.status_code == 200
    summary = response.json()
    assert summary["topic"] == "RAG evaluation"
    assert summary["validated_cards_count"] == 1
    assert summary["errors_count"] == 0
    get_settings.cache_clear()
