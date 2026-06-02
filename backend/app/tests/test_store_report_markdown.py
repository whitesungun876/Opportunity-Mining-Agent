"""Report persistence tests."""

from app.memory.run_store import RunStore
from app.tests.test_run_store_create_and_read import _state


def test_store_report_markdown(tmp_path):
    store = RunStore(f"sqlite:///{tmp_path / 'report.db'}")
    state = _state()
    store.save_run_state(state)

    report = store.get_report(state["run_id"])

    assert report
    assert "https://github.com/example/rag/issues/1" in report
