"""Run store persistence tests."""

from app.memory.run_store import RunStore


def _state() -> dict:
    return {
        "run_id": "run_store_test",
        "user_query": "RAG evaluation",
        "canonical_topic": "RAG evaluation",
        "search_plan": {"topic": "RAG evaluation", "repo_search_queries": ["RAG evaluation stars:>100"]},
        "selected_repos": [{"repo_id": "repo_1", "full_name": "example/rag", "url": "https://github.com/example/rag"}],
        "evidence_items": [
            {
                "evidence_id": "ev_1",
                "source_url": "https://github.com/example/rag/issues/1",
                "repo_url": "https://github.com/example/rag",
                "title": "Need production evaluation",
            },
            {
                "evidence_id": "ev_2",
                "source_url": "https://github.com/example/rag/issues/2",
                "repo_url": "https://github.com/example/rag",
                "title": "Debug failed retrieval",
            },
            {
                "evidence_id": "ev_3",
                "source_url": "https://github.com/example/rag/issues/3",
                "repo_url": "https://github.com/example/rag",
                "title": "Track quality regressions",
            },
        ],
        "pain_points": [{"pain_id": "pain_1", "evidence_id": "ev_1", "complaint": "Evaluation is hard."}],
        "pain_clusters": [{"cluster_id": "cluster_1", "evidence_ids": ["ev_1", "ev_2", "ev_3"]}],
        "commercial_gaps": [{"gap_id": "gap_1", "evidence_ids": ["ev_1", "ev_2", "ev_3"]}],
        "opportunity_cards": [
            {
                "opportunity_id": "opp_1",
                "title": "Hosted RAG Evaluation Dashboard",
                "migration_cost": "medium",
                "evidence_ids": ["ev_1", "ev_2", "ev_3"],
            }
        ],
        "validated_cards": [
            {
                "opportunity_id": "opp_1",
                "title": "Hosted RAG Evaluation Dashboard",
                "migration_cost": "medium",
                "evidence_ids": ["ev_1", "ev_2", "ev_3"],
                "evidence_urls": [
                    "https://github.com/example/rag/issues/1",
                    "https://github.com/example/rag/issues/2",
                    "https://github.com/example/rag/issues/3",
                ],
            }
        ],
        "rejected_cards": [],
        "agent_reviews": [{"opportunity_id": "opp_1", "agent": "PM", "score": 8}],
        "final_decisions": [{"opportunity_id": "opp_1", "decision": "validate", "score": 78}],
        "report_markdown": "# Report\n\nhttps://github.com/example/rag/issues/1",
        "errors": [],
    }


def test_run_store_create_and_read(tmp_path):
    store = RunStore(f"sqlite:///{tmp_path / 'runs.db'}")
    saved = store.save_run_state(_state(), topic="RAG evaluation", dynamic_search=True)

    loaded = store.get_run(saved["run_id"])
    summary = store.get_summary(saved["run_id"])

    assert loaded is not None
    assert loaded["run_id"] == "run_store_test"
    assert loaded["status"] == "completed"
    assert loaded["dynamic_search"] is True
    assert summary is not None
    assert summary["topic"] == "RAG evaluation"
    assert summary["validated_cards_count"] == 1
    assert summary["evidence_items_count"] == 3
