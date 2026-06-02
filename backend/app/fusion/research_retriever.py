"""Curated research evidence retrieval for opportunity fusion."""

from __future__ import annotations

from typing import Any

from app.fusion.schemas import ResearchEvidence


CURATED_RESEARCH = [
    ResearchEvidence(
        paper_id="paper_rag_eval_001",
        title="RAGAS: Automated Evaluation of Retrieval Augmented Generation",
        url="https://arxiv.org/abs/2309.15217",
        abstract="Proposes reference-free metrics for evaluating retrieval augmented generation pipelines.",
        claim_summary="RAG quality can be evaluated with structured metrics for faithfulness, answer relevance, and context relevance.",
        supports=["rag evaluation", "evaluation and regression testing", "quality gates"],
        limitation="Supports technical evaluation methods, not willingness to pay.",
        confidence=0.78,
    ),
    ResearchEvidence(
        paper_id="paper_agent_eval_001",
        title="AgentBench: Evaluating LLMs as Agents",
        url="https://arxiv.org/abs/2308.03688",
        abstract="Benchmarks LLM agents across environments and tasks.",
        claim_summary="Agent behavior can be evaluated through task trajectories and environment-level outcomes.",
        supports=["agent evaluation", "tool calling", "trajectory evaluation"],
        limitation="Does not prove a commercial market for agent debugging tools.",
        confidence=0.72,
    ),
    ResearchEvidence(
        paper_id="paper_toolformer_001",
        title="Toolformer: Language Models Can Teach Themselves to Use Tools",
        url="https://arxiv.org/abs/2302.04761",
        abstract="Studies language-model tool use and self-supervised tool-call behavior.",
        claim_summary="Tool-use behavior can be represented and inspected as structured model actions.",
        supports=["tool calling", "agent debugging", "tool-use replay"],
        limitation="Method paper only; production workflow demand must come from GitHub evidence.",
        confidence=0.68,
    ),
    ResearchEvidence(
        paper_id="paper_observability_001",
        title="Debugging Machine Learning Pipelines",
        url="https://arxiv.org/abs/2205.00000",
        abstract="Representative research direction around debugging and monitoring ML systems.",
        claim_summary="Production ML systems need traceable pipeline stages to isolate failures and regressions.",
        supports=["observability", "tracing and observability", "production debugging"],
        limitation="Curated placeholder evidence; replace with verified paper sources for paid reports.",
        confidence=0.55,
    ),
]


def _context_text(state: dict[str, Any]) -> str:
    chunks = [
        str(state.get("user_query") or ""),
        str(state.get("canonical_topic") or ""),
        " ".join(str(cap.get("name") or "") for cap in state.get("repo_capabilities") or []),
        " ".join(str(pain.get("pain_type") or "") for pain in state.get("pain_points") or []),
        " ".join(str(pain.get("complaint") or "") for pain in state.get("pain_points") or []),
    ]
    return " ".join(chunks).lower()


class ResearchRetriever:
    """Retrieve small curated paper evidence for technical feasibility support."""

    def retrieve(self, state: dict[str, Any], *, limit: int = 3) -> list[dict[str, Any]]:
        text = _context_text(state)
        scored: list[tuple[float, ResearchEvidence]] = []
        for paper in CURATED_RESEARCH:
            support_hits = sum(1 for support in paper.supports if support.lower() in text)
            title_hits = sum(1 for token in paper.title.lower().split() if len(token) > 4 and token in text)
            score = support_hits * 0.4 + title_hits * 0.1 + paper.confidence * 0.5
            if score > 0.25:
                scored.append((score, paper))
        return [
            {
                **paper.model_dump(),
                "retrieval_score": round(score, 3),
                "evidence_role": "technical_feasibility",
            }
            for score, paper in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]
        ]


def retrieve_research_evidence(state: dict[str, Any], *, limit: int = 3) -> list[dict[str, Any]]:
    return ResearchRetriever().retrieve(state, limit=limit)
