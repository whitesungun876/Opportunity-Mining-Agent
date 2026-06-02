"""Benchmark topic profile tests."""

from app.eval.topic_profiles import list_profiles, resolve_profile


def test_resolve_profile_by_alias():
    profile = resolve_profile(topic="RAG evaluation")

    assert profile.profile_id == "rag_evaluation"
    assert profile.queries
    assert any("langfuse" in query for query in profile.queries)


def test_resolve_profile_falls_back_to_generic():
    profile = resolve_profile(topic="vector database")

    assert profile.profile_id == "generic"
    assert any("{topic}" in query for query in profile.queries)
    assert any("vector database" in query for query in profile.render_queries("vector database"))


def test_list_profiles_includes_benchmark_profiles():
    profiles = list_profiles()

    assert "rag_evaluation" in profiles
    assert "mcp_tools" in profiles
    assert "generic" in profiles
