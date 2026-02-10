"""Reporter smoke test: markdown report contains title, theme, and Evidence section."""

from src.nodes.reporter import reporter_node
from src.utils.schema import PainPoint, OpportunityCluster


def test_reporter_smoke():
    cluster = OpportunityCluster(
        theme="Subscription/tiering causes low-frequency user resentment; desire for pay-per-use",
        pain_points=[
            PainPoint(
                complaint="Subscription too expensive",
                cause="Must pay monthly even for low usage",
                persona="Low-frequency user",
                context="Occasional use",
                action_intent="Want pay-per-use",
                evidence=["Having to buy a full month every time is painful."],
            )
        ],
        sample_size=1,
        confidence=0.7,
    )

    out = reporter_node(
        {"topic": "AI tool complaints", "opportunity_clusters": [cluster]},
        top_k=3,
    )
    md = out["report_markdown"]

    assert "Startup Oracle Report" in md
    assert "Subscription/tiering" in md
    assert "Evidence" in md
