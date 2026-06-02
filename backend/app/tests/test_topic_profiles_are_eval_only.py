"""topic_profiles.yaml must remain an eval-only benchmark fixture."""

from app.graph.main_graph import run_graph
from app.search.planner import generate_search_plan


def test_product_search_plan_is_dynamic_not_eval_profile():
    plan = generate_search_plan("RAG evaluation")

    assert plan.source == "dynamic"


def test_product_graph_does_not_require_benchmark_profile():
    state = run_graph("vector database")

    assert state["search_plan"]["source"] == "dynamic"
    assert "benchmark_profile" not in state
    assert state["search_plan"]["global_issue_queries"]
