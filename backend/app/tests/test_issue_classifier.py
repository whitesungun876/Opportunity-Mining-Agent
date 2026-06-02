"""Issue classifier rule tests."""

from app.nodes.issue_classify import classify_issue


def test_issue_classifier_high_value_production_gap():
    issue = {
        "issue_id": "1",
        "title": "Need observability for failing retrieval traces",
        "body": "This is blocking production deployment.",
        "labels": [],
        "url": "https://github.com/mock/repo/issues/1",
    }
    out = classify_issue(issue)
    assert out["value_class"] == "high_value"
    assert out["reason"] in {
        "observability/evaluation/debugging gap",
        "production deployment blocker",
    }


def test_issue_classifier_low_value_install_error():
    issue = {
        "issue_id": "2",
        "title": "pip install fails on my laptop",
        "body": "local env issue",
        "labels": [],
        "url": "https://github.com/mock/repo/issues/2",
    }
    out = classify_issue(issue)
    assert out["value_class"] == "low_value"
