"""Embedding client deterministic fallback tests."""

from app.services.embedding_client import EmbeddingClient, deterministic_embedding
from app.services.clustering import cosine_similarity


def test_embedding_client_mock_fallback_is_deterministic(tmp_path):
    client = EmbeddingClient(api_key=None, mock_mode=True, cache_path=tmp_path / "emb.sqlite")
    texts = ["production deployment tracing", "production deployment tracing"]

    vectors = client.embed_batch(texts)

    assert vectors[0] == vectors[1]
    assert len(vectors[0]) == 64


def test_deterministic_embedding_keeps_similar_texts_close():
    left = deterministic_embedding("production deployment tracing dashboard")
    right = deterministic_embedding("production deployment trace dashboard")
    unrelated = deterministic_embedding("local pip install windows laptop")

    assert cosine_similarity(left, right) > cosine_similarity(left, unrelated)
