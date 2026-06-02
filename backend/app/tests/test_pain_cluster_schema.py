"""Pain cluster schema tests."""

from app.services.clustering import cluster_pain_points
from app.services.embedding_client import EmbeddingClient


def test_pain_cluster_schema(tmp_path):
    pains = [
        {
            "pain_id": "pain_1",
            "evidence_id": "ev1",
            "pain_type": "deployment_complexity",
            "complaint": "Production deployment is hard",
            "severity": 0.8,
            "supporting_quote": "Deployment is hard",
        },
        {
            "pain_id": "pain_2",
            "evidence_id": "ev2",
            "pain_type": "deployment_complexity",
            "complaint": "Self-hosted deployment needs Kubernetes templates",
            "severity": 0.7,
            "supporting_quote": "Need Kubernetes templates",
        },
    ]
    evidence = [
        {"evidence_id": "ev1", "repo_owner": "o", "repo_name": "r1"},
        {"evidence_id": "ev2", "repo_owner": "o", "repo_name": "r2"},
    ]
    client = EmbeddingClient(mock_mode=True, cache_path=tmp_path / "emb.sqlite")

    clusters = cluster_pain_points(pains, evidence_items=evidence, embedding_client=client)

    assert clusters
    cluster = clusters[0]
    assert {
        "cluster_id",
        "topic",
        "theme",
        "pain_type",
        "pain_ids",
        "evidence_ids",
        "evidence_count",
        "repo_count",
        "severity_score",
        "repetition_score",
        "summary",
        "example_quotes",
    }.issubset(cluster)
