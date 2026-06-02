"""WTP signal detection tests."""

from app.commercial.wtp_signal import detect_wtp_signal
from app.commercial.schemas import WillingnessToPaySignal


def test_wtp_signal_detects_enterprise_payment_hypothesis():
    card = {
        "opportunity_id": "opp_1",
        "title": "RBAC dashboard",
        "pricing_hypothesis": "Hypothesis: teams may pay after validation.",
        "evidence_ids": ["ev_1", "ev_2", "ev_3"],
    }
    evidence = [
        {
            "evidence_id": "ev_1",
            "title": "Need enterprise SSO and audit logs",
            "body": "Security team needs RBAC before production deployment.",
            "comment_count": 6,
        },
        {"evidence_id": "ev_2", "title": "Permission issue", "body": "RBAC", "comment_count": 2},
        {"evidence_id": "ev_3", "title": "Compliance workflow", "body": "audit", "comment_count": 1},
    ]

    signal = WillingnessToPaySignal(**detect_wtp_signal(card, evidence))

    assert signal.opportunity_id == "opp_1"
    assert signal.strength in {"medium", "strong"}
    assert "Payment hypothesis" in signal.signal_summary
