"""Langfuse observer tests."""

from app.config import Settings
from app.harness.langfuse_observer import LangfuseObserver, score_payload


def test_score_payload_maps_summary_to_trace_scores():
    scores = score_payload(
        {
            "opportunity_cards": 4,
            "validated_cards": 2,
            "rejected_cards": 2,
            "high_value_issues": 12,
            "pain_points": 10,
            "errors": 0,
            "report_has_github": True,
        }
    )

    assert scores["validated_rate"] == 0.5
    assert scores["strict_pass"] == 1.0
    assert scores["report_has_github"] == 1.0


def test_langfuse_observer_is_noop_when_disabled():
    observer = LangfuseObserver(Settings(langfuse_enabled=False))

    with observer.trace(name="test", input_data={}, metadata={}):
        with observer.node_span(node_name="node", input_data={}):
            pass

    observer.score_run({"validated_cards": 0})
    observer.flush()
    assert observer.enabled is False
    assert observer.errors == []
