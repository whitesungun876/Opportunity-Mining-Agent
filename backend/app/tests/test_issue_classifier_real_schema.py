"""Real classifier schema parsing tests without a real LLM call."""

from app.nodes.issue_classify import parse_issue_classifier_response


def test_parse_issue_classifier_response_normalizes_schema():
    issue = {
        "issue_id": "ev_123",
        "url": "https://github.com/owner/repo/issues/123",
        "title": "Need evaluation traces in production",
        "body": "We cannot debug production failures.",
    }
    fake_response = {
        "evidence_id": "ev_123",
        "value_level": "high_value",
        "category": "observability/evaluation/debugging gap",
        "reason": "The user is blocked while debugging production failures.",
        "labels_matched": ["production", "debug"],
        "should_extract_pain": True,
    }

    parsed = parse_issue_classifier_response(fake_response, issue)

    assert parsed["evidence_id"] == "ev_123"
    assert parsed["value_level"] == "high_value"
    assert parsed["value_class"] == "high_value"
    assert parsed["reason"]
    assert parsed["labels_matched"] == ["production", "debug"]
    assert parsed["should_extract_pain"] is True


def test_parse_issue_classifier_response_invalid_level_defaults_low():
    issue = {"issue_id": "ev_456", "title": "pip install fails"}
    parsed = parse_issue_classifier_response({"value_level": "maybe"}, issue)

    assert parsed["value_level"] == "low_value"
    assert parsed["should_extract_pain"] is False
