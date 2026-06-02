"""Badcase regression runner tests."""

from app.eval.badcase_runner import run_badcases


def test_badcase_runner_all_cases_pass():
    result = run_badcases()

    assert result["total"] >= 10
    assert result["failed"] == 0


def test_badcase_runner_stage_filter():
    result = run_badcases(stage="issue_classify")

    assert result["stage"] == "issue_classify"
    assert result["total"] == 3
    assert result["failed"] == 0
