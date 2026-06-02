"""FastAPI run creation tests."""

from fastapi.testclient import TestClient
import time

from app.api import runs as runs_api
from app.config import get_settings
from app.main import app
from app.tests.test_run_store_create_and_read import _state


def test_api_create_run_mock(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'api_create.db'}")
    get_settings.cache_clear()
    monkeypatch.setattr(runs_api, "run_graph", lambda topic, initial_state=None: _state())

    client = TestClient(app)
    response = client.post("/runs", json={"topic": "RAG evaluation", "dynamic_search": True})

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"]
    assert payload["status"] in {"queued", "running", "completed"}

    for _ in range(20):
        status = client.get(f"/runs/{payload['run_id']}/status").json()
        if status["status"] == "completed":
            break
        time.sleep(0.05)
    assert status["status"] == "completed"

    loaded = client.get(f"/runs/{payload['run_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["validated_cards"][0]["opportunity_id"] == "opp_1"
    get_settings.cache_clear()
