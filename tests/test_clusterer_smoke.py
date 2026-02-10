"""Clusterer smoke test: offline (fake LLM) returns valid OpportunityClusters."""

from src.nodes.clusterer import ClusterList, clusterer_node
from src.utils.schema import OpportunityCluster, PainPoint


class FakeStructuredLLM:
    def invoke(self, messages):
        # Return a valid clustering: merge two pains into one theme
        pains = [
            PainPoint(
                complaint="Subscription too expensive",
                cause="Must pay monthly even for low usage",
                persona="Low-frequency user",
                context="Occasional use",
                action_intent="Want pay-per-use or one-time payment",
                evidence=["Having to buy a full month every time is painful."],
            ),
            PainPoint(
                complaint="Basic tier unusable",
                cause="Features locked behind membership tiers",
                persona="Casual user",
                context="Just downloaded for trial",
                action_intent="Looking for alternatives",
                evidence=["Basic tier can't do anything."],
            ),
        ]
        return ClusterList(
            items=[
                OpportunityCluster(
                    theme="Subscription/tiering causes low-frequency user resentment; desire for pay-per-use or clearer feature unlock",
                    pain_points=pains,
                    sample_size=2,
                    confidence=0.7,
                )
            ]
        )


class FakeLLM:
    def with_structured_output(self, _schema):
        return FakeStructuredLLM()


def test_clusterer_smoke_offline():
    pains = [
        PainPoint(
            complaint="Subscription too expensive",
            cause="Must pay monthly even for low usage",
            persona="Low-frequency user",
            context="Occasional use",
            action_intent="Want pay-per-use or one-time payment",
            evidence=["Having to buy a full month every time is painful."],
        )
    ]
    state = {"extracted_pains": pains, "_llm_factory": lambda: FakeLLM()}

    out = clusterer_node(state, max_retries=0)
    clusters = out.get("opportunity_clusters", [])

    assert len(clusters) >= 1
    assert clusters[0].sample_size == len(clusters[0].pain_points)
    assert 0.0 <= clusters[0].confidence <= 1.0
