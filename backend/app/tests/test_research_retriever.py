"""Research evidence retriever tests."""

from app.fusion.research_retriever import retrieve_research_evidence


def test_research_retriever_returns_technical_feasibility_evidence():
    state = {
        "user_query": "RAG evaluation regression testing before deployment",
        "repo_capabilities": [{"name": "Evaluation and regression testing"}],
        "pain_points": [{"pain_type": "evaluation_gap", "complaint": "Teams need RAG evaluation quality gates."}],
    }

    papers = retrieve_research_evidence(state)

    assert papers
    assert all(item["evidence_role"] == "technical_feasibility" for item in papers)
    assert all("willingness" not in item["claim_summary"].lower() for item in papers)
    assert any("RAGAS" in item["title"] for item in papers)
