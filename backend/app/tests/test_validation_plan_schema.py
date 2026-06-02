"""Validation plan schema tests."""

from app.commercial.schemas import ValidationPlan
from app.commercial.validation_plan import build_validation_plan


def test_validation_plan_schema():
    card = {"opportunity_id": "opp_1", "title": "Hosted Debugging Dashboard", "evidence_ids": ["ev_1", "ev_2", "ev_3"]}
    plan = ValidationPlan(**build_validation_plan(card, [{"opportunity_id": "opp_1", "strength": "medium"}]))

    assert plan.opportunity_id == "opp_1"
    assert len(plan.seven_day_plan) == 7
    assert plan.recommended_next_step in {"build", "validate", "watch", "reject"}
