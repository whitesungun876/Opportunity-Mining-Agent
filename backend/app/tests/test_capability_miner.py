"""Capability discovery tests."""

from app.fusion.capability_miner import discover_capabilities


def test_capability_miner_extracts_transferable_repo_capabilities():
    state = {
        "selected_repos": [
            {
                "full_name": "langfuse/langfuse",
                "description": "LLM observability tracing and evaluation platform",
                "stars": 12000,
            }
        ],
        "evidence_items": [
            {
                "evidence_id": "ev_001",
                "repo_owner": "langfuse",
                "repo_name": "langfuse",
                "title": "Need trace replay for production debugging",
                "body": "Teams need observability, tracing, and eval dashboards.",
                "matched_signals": ["trace", "observability", "evaluation", "dashboard"],
            }
        ],
    }

    capabilities = discover_capabilities(state)
    names = {item["name"] for item in capabilities}

    assert "Tracing and observability" in names
    assert "Evaluation and regression testing" in names
    assert all(item["source_repo"] == "langfuse/langfuse" for item in capabilities)
    assert all("capability_id" in item for item in capabilities)
