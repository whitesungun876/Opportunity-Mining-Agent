"""Outreach target source tests."""

from app.commercial.outreach_targets import build_outreach_targets


def test_outreach_targets_have_source_url():
    cards = [{"opportunity_id": "opp_1", "evidence_ids": ["ev_1"]}]
    evidence = [
        {
            "evidence_id": "ev_1",
            "author_login": "octocat",
            "source_url": "https://github.com/o/r/issues/1",
            "repo_owner": "o",
            "repo_name": "r",
        }
    ]
    pains = [{"evidence_id": "ev_1", "pain_type": "deployment_complexity"}]

    targets = build_outreach_targets(cards, evidence, pains)

    assert targets
    assert targets[0]["source_url"] == "https://github.com/o/r/issues/1"
    assert targets[0]["github_user"] == "octocat"
