"""Live quality audit artifact tests."""

from app.eval.live_quality import run_live_quality


def test_live_quality_dynamic_mode_writes_search_plan_artifact(tmp_path):
    state, artifact_dir, summary = run_live_quality(
        topic="MCP tools",
        per_query=None,
        max_issues=None,
        output_dir=tmp_path,
        dynamic_search=True,
        skip_debate=True,
    )

    assert summary["mode"] == "dynamic"
    assert state["search_plan"]["source"] == "dynamic"
    assert (artifact_dir / "search_plan.json").exists()
    assert (artifact_dir / "opportunity_cards.json").exists()
