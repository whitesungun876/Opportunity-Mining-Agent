"""EvidenceQualityRanker tests."""

from app.search.planner import generate_search_plan
from app.search.scorer import EvidenceQualityRanker


def test_evidence_quality_ranker_adds_score_and_reason():
    plan = generate_search_plan("RAG evaluation").model_dump()
    evidence = [
        {
            "evidence_id": "ev_low",
            "title": "pip install fails on my laptop",
            "body": "Local environment issue.",
            "source_url": "https://github.com/o/r/issues/1",
            "comment_count": 1,
            "reaction_count": 0,
            "repo_owner": "o",
            "repo_name": "r",
            "state": "OPEN",
        },
        {
            "evidence_id": "ev_high",
            "title": "Production deployment needs tracing and evaluation dashboard",
            "body": "At scale we need observability, metrics, and enterprise permission workflows.",
            "source_url": "https://github.com/o/r/issues/2",
            "comment_count": 9,
            "reaction_count": 4,
            "repo_owner": "o",
            "repo_name": "r2",
            "state": "OPEN",
        },
    ]

    ranked = EvidenceQualityRanker(plan).rank(evidence)

    assert ranked[0]["evidence_id"] == "ev_high"
    assert ranked[0]["evidence_quality_score"] > ranked[1]["evidence_quality_score"]
    assert ranked[0]["matched_signals"]
    assert ranked[0]["rank_reason"]
