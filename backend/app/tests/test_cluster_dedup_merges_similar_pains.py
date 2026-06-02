"""Cluster deduplication tests."""

from app.services.clustering import dedupe_pain_clusters, merge_sparse_same_type_clusters
from app.services.embedding_client import EmbeddingClient


def test_cluster_dedup_merges_similar_pains(tmp_path):
    clusters = [
        {
            "cluster_id": "cluster_a",
            "pain_type": "deployment_complexity",
            "theme": "Production deployment is hard",
            "summary": "Users need production deployment workflow",
            "pain_ids": ["pain_1"],
            "evidence_ids": ["ev1", "ev2"],
            "evidence_count": 2,
            "repo_count": 1,
            "severity_score": 0.8,
            "repetition_score": 0.4,
            "example_quotes": ["production deployment is hard"],
        },
        {
            "cluster_id": "cluster_b",
            "pain_type": "production_deployment_blocker",
            "theme": "Production deployment is hard",
            "summary": "Users need production deployment workflow",
            "pain_ids": ["pain_2"],
            "evidence_ids": ["ev2", "ev3"],
            "evidence_count": 2,
            "repo_count": 2,
            "severity_score": 0.7,
            "repetition_score": 0.4,
            "example_quotes": ["deployment blocker"],
        },
    ]
    client = EmbeddingClient(mock_mode=True, cache_path=tmp_path / "emb.sqlite")

    deduped = dedupe_pain_clusters(clusters, embedding_client=client)

    assert len(deduped) == 1
    assert set(deduped[0]["evidence_ids"]) == {"ev1", "ev2", "ev3"}
    assert set(deduped[0]["pain_ids"]) == {"pain_1", "pain_2"}


def test_sparse_same_type_clusters_merge_when_evidence_repeats():
    clusters = [
        {
            "cluster_id": "cluster_1",
            "pain_type": "missing_workflow",
            "theme": "GitOps deployment workflow is missing",
            "pain_ids": ["pain_1"],
            "evidence_ids": ["ev1"],
            "evidence_count": 1,
            "repo_count": 1,
            "severity_score": 0.8,
            "repetition_score": 0.2,
            "example_quotes": ["need GitOps deployment"],
        },
        {
            "cluster_id": "cluster_2",
            "pain_type": "missing_workflow",
            "theme": "Native security dashboard workflow is missing",
            "pain_ids": ["pain_2"],
            "evidence_ids": ["ev2"],
            "evidence_count": 1,
            "repo_count": 1,
            "severity_score": 0.7,
            "repetition_score": 0.2,
            "example_quotes": ["need native dashboards"],
        },
        {
            "cluster_id": "cluster_3",
            "pain_type": "missing_workflow",
            "theme": "Alerting workflow needs better RBAC",
            "pain_ids": ["pain_3"],
            "evidence_ids": ["ev3"],
            "evidence_count": 1,
            "repo_count": 1,
            "severity_score": 0.75,
            "repetition_score": 0.2,
            "example_quotes": ["folder RBAC blocks alerts"],
        },
    ]
    evidence = [
        {"evidence_id": "ev1", "repo_owner": "grafana", "repo_name": "grafana"},
        {"evidence_id": "ev2", "repo_owner": "grafana", "repo_name": "grafana"},
        {"evidence_id": "ev3", "repo_owner": "grafana", "repo_name": "grafana"},
    ]

    merged = merge_sparse_same_type_clusters(clusters, evidence_items=evidence)

    assert len(merged) == 1
    assert merged[0]["evidence_count"] == 3
    assert set(merged[0]["evidence_ids"]) == {"ev1", "ev2", "ev3"}
    assert set(merged[0]["merged_from"]) == {"cluster_1", "cluster_2", "cluster_3"}
