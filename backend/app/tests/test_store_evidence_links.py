"""Evidence link persistence tests."""

from app.memory.run_store import RunStore
from app.tests.test_run_store_create_and_read import _state


def test_store_evidence_links(tmp_path):
    store = RunStore(f"sqlite:///{tmp_path / 'evidence.db'}")
    store.save_run_state(_state())

    evidence = store.get_opportunity_evidence("opp_1")

    assert len(evidence) == 3
    assert all(item["source_url"].startswith("https://github.com/") for item in evidence)
    assert evidence[0]["evidence_id"] == "ev_1"
