"""Fusion candidate generation tests."""

from app.fusion.fusion_generator import generate_fusion_candidates


def test_fusion_generator_combines_pain_capability_and_research():
    state = {
        "canonical_topic": "RAG evaluation",
        "pain_points": [
            {
                "pain_id": "pain_001",
                "evidence_id": "ev_001",
                "pain_type": "evaluation_gap",
                "complaint": "Teams need regression checks before shipping RAG updates.",
                "severity": 0.8,
                "persona": "RAG platform teams",
            }
        ],
        "repo_capabilities": [
            {
                "capability_id": "cap_langfuse_evaluation",
                "name": "Evaluation and regression testing",
                "description": "Compares outputs against datasets and metrics.",
                "source_repo": "langfuse/langfuse",
                "maturity_score": 0.82,
                "related_methods": ["regression dataset comparison", "metric scoring"],
                "evidence_ids": ["ev_002"],
            }
        ],
        "research_evidence": [
            {
                "paper_id": "paper_rag_eval_001",
                "title": "RAGAS",
                "confidence": 0.78,
                "supports": ["rag evaluation", "evaluation and regression testing"],
            }
        ],
    }

    candidates = generate_fusion_candidates(state)

    assert candidates
    candidate = candidates[0]
    assert candidate["evidence_ids"] == ["ev_001", "ev_002"]
    assert candidate["repo_ids"] == ["langfuse/langfuse"]
    assert candidate["paper_ids"] == ["paper_rag_eval_001"]
    assert candidate["overall_score"] > 0
