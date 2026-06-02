"""Query scope detection tests."""

from app.search.scope import detect_query_scope_rules


def test_query_scope_ambiguous_single_word():
    scope = detect_query_scope_rules("agent")

    assert scope.scope == "ambiguous"
    assert scope.refinement_required is True
    assert scope.suggested_queries


def test_query_scope_broad_category():
    scope = detect_query_scope_rules("AI agent framework")

    assert scope.scope == "broad"
    assert scope.refinement_required is False


def test_query_scope_focused_problem():
    scope = detect_query_scope_rules("AI agent framework observability for production debugging")

    assert scope.scope == "focused"
    assert scope.specificity_score >= 0.65


def test_query_scope_repo_specific_owner_repo():
    scope = detect_query_scope_rules("langfuse/langfuse")

    assert scope.scope == "repo_specific"
    assert scope.repo_owner == "langfuse"
    assert scope.repo_name == "langfuse"
    assert scope.normalized_query == "langfuse/langfuse"


def test_query_scope_repo_specific_github_url():
    scope = detect_query_scope_rules("https://github.com/langfuse/langfuse/issues")

    assert scope.scope == "repo_specific"
    assert scope.repo_owner == "langfuse"
    assert scope.repo_name == "langfuse"
