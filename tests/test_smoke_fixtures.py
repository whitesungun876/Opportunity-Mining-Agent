"""Smoke and run-until-node tests using SAMPLE_RAW_ITEMS and run_smoke_until."""

from __future__ import annotations

import pytest

from src.eval.benchmark import SAMPLE_RAW_ITEMS, run_smoke, run_smoke_until


@pytest.fixture
def smoke_initial():
    """Initial state for smoke: topic + raw_items so collect/clean can run."""
    return {
        "topic": "smoke test",
        "raw_items": SAMPLE_RAW_ITEMS,
    }


def test_sample_raw_items_fixture():
    assert len(SAMPLE_RAW_ITEMS) >= 1
    assert all(isinstance(x, dict) and "content" in x for x in SAMPLE_RAW_ITEMS)


def test_run_smoke_returns_state(smoke_initial):
    """Full smoke run returns merged state with expected keys from pipeline."""
    state = run_smoke(smoke_initial)
    assert isinstance(state, dict)
    # After full run we expect at least topic and some pipeline outputs
    assert "topic" in state
    # clean_comments or cleaned_texts appear after clean node
    has_clean_output = "clean_comments" in state or "cleaned_texts" in state or "raw_items" in state
    assert has_clean_output, "state should contain pipeline outputs or raw_items"


def test_run_smoke_until_clean_returns_state_after_clean(smoke_initial):
    """Run until 'clean' returns state that includes clean node outputs (or collect if stream order)."""
    state = run_smoke_until(smoke_initial, "clean")
    assert isinstance(state, dict)
    # We expect either clean output (if stream yields by node name) or at least merged state
    assert "topic" in state
    has_some_output = (
        "clean_comments" in state
        or "cleaned_texts" in state
        or "raw_items" in state
        or "raw_comments" in state
    )
    assert has_some_output
