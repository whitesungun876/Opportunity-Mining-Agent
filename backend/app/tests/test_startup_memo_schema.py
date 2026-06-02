"""Startup memo schema tests."""

from app.commercial.schemas import StartupMemo
from app.commercial.startup_memo import build_startup_memos


def test_startup_memo_schema():
    cards = [
        {
            "opportunity_id": "opp_1",
            "title": "Hosted Debugging Dashboard",
            "pain_summary": "Teams cannot debug production traces.",
            "commercial_gap": "Hosted workflow gap.",
            "mvp_features": ["Trace ingestion"],
            "pricing_hypothesis": "Hypothesis: teams may pay after validation.",
            "risks": ["Competition"],
            "evidence_ids": ["ev_1", "ev_2", "ev_3"],
        }
    ]
    memos = build_startup_memos(
        cards,
        buyer_hypotheses=[{"opportunity_id": "opp_1", "economic_buyer": "Hypothesis: Head of Engineering", "end_user": "Hypothesis: AI teams"}],
        wtp_signals=[{"opportunity_id": "opp_1", "strength": "medium", "signal_summary": "Payment hypothesis: possible budgeted pain."}],
        alternatives=[{"opportunity_id": "opp_1", "name": "Manual process", "limitation": "Slow"}],
        outreach_targets=[{"opportunity_id": "opp_1", "github_user": "octocat", "source_url": "https://github.com/o/r/issues/1"}],
        validation_plans=[{"opportunity_id": "opp_1", "seven_day_plan": ["Day 1: Contact users."], "recommended_next_step": "validate"}],
        final_decisions=[{"opportunity_id": "opp_1", "decision": "validate"}],
    )

    memo = StartupMemo(**memos[0])

    assert memo.opportunity_id == "opp_1"
    assert memo.final_decision == "validate"
    assert "Hypothesis" in memo.target_buyer
