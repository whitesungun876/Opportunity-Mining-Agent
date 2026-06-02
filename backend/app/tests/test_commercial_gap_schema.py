"""Commercial gap schema parsing tests."""

from app.nodes.commercial_gap import parse_commercial_gap_response


def test_parse_commercial_gap_response_normalizes_schema():
    cluster = {
        "cluster_id": "cluster_1",
        "theme": "Production evaluation workflow",
        "evidence_ids": ["ev1", "ev2", "ev3"],
    }
    response = {
        "gap_id": "gap_1",
        "cluster_id": "cluster_1",
        "commercial_gap_type": "Monitoring / evaluation dashboard gap",
        "gap_summary": "Teams need a hosted evaluation dashboard.",
        "why_open_source_is_not_enough": "Open-source primitives lack a workflow layer.",
        "who_would_pay": "AI platform teams",
        "best_product_form": "Hosted SaaS",
        "migration_cost": "low",
        "migration_cost_reason": "A hosted dashboard can integrate via SDK.",
        "consulting_vs_saas": "saas_possible",
        "why_now": "More teams are productionizing RAG.",
        "confidence": 0.82,
        "evidence_ids": ["ev1", "ev2", "ev3", "bad"],
    }

    parsed = parse_commercial_gap_response(response, cluster)

    assert parsed["gap_id"] == "gap_1"
    assert parsed["commercial_gap_type"] == "Monitoring / evaluation dashboard gap"
    assert parsed["best_product_form"] == "Hosted SaaS"
    assert parsed["migration_cost"] == "low"
    assert parsed["consulting_vs_saas"] == "saas_possible"
    assert parsed["confidence"] == 0.82
    assert parsed["evidence_ids"] == ["ev1", "ev2", "ev3"]
