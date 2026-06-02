"""Generate cross-source opportunity fusion candidates."""

from __future__ import annotations

import re
from typing import Any

from app.fusion.fusion_scorer import score_fusion_candidate
from app.fusion.schemas import FusionCandidate


PAIN_CAPABILITY_HINTS = {
    "observability_gap": ["tracing", "observability", "dashboard"],
    "evaluation_gap": ["evaluation", "regression", "dashboard"],
    "performance_at_scale": ["tracing", "observability", "deployment"],
    "deployment_complexity": ["deployment", "managed"],
    "configuration_complexity": ["deployment", "workflow"],
    "integration_gap": ["integration", "connector", "workflow"],
    "enterprise_security_gap": ["enterprise", "access", "security"],
    "permission_gap": ["enterprise", "access", "permission"],
    "missing_ui": ["dashboard", "review"],
    "missing_workflow": ["workflow", "integration", "dashboard"],
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:60]


def _evidence_ids(*items: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item.get("evidence_id"):
            out.append(str(item["evidence_id"]))
        out.extend(str(value) for value in item.get("evidence_ids") or [])
    return list(dict.fromkeys(item for item in out if item))


def _capability_matches_pain(pain: dict[str, Any], capability: dict[str, Any]) -> bool:
    pain_type = str(pain.get("pain_type") or "unclear")
    pain_text = f"{pain_type} {pain.get('complaint', '')} {pain.get('business_signal', '')}".lower()
    cap_text = f"{capability.get('name', '')} {capability.get('description', '')} {' '.join(capability.get('related_methods') or [])}".lower()
    hints = PAIN_CAPABILITY_HINTS.get(pain_type, [])
    if any(hint in cap_text for hint in hints):
        return True
    return bool(set(token for token in pain_text.split() if len(token) > 5).intersection(cap_text.split()))


def _related_research(capability: dict[str, Any], research: list[dict[str, Any]], limit: int = 2) -> list[dict[str, Any]]:
    cap_text = f"{capability.get('name', '')} {capability.get('description', '')} {' '.join(capability.get('related_methods') or [])}".lower()
    matches = []
    for paper in research:
        supports = " ".join(str(item) for item in paper.get("supports") or []).lower()
        score = sum(1 for token in cap_text.split() if len(token) > 5 and token in supports)
        if score or any(method.lower() in supports for method in capability.get("related_methods") or []):
            matches.append((score + float(paper.get("confidence") or 0), paper))
    return [paper for _, paper in sorted(matches, key=lambda item: item[0], reverse=True)[:limit]]


def _human_pain(pain: dict[str, Any]) -> str:
    complaint = str(pain.get("complaint") or "").strip()
    if complaint:
        return complaint.rstrip(".")
    return str(pain.get("pain_type") or "production workflow gap").replace("_", " ")


def _title(capability: dict[str, Any], pain: dict[str, Any]) -> str:
    cap_name = str(capability.get("name") or "Productized workflow")
    raw_pain_type = str(pain.get("pain_type") or "").strip()
    if raw_pain_type and raw_pain_type != "unclear":
        pain_type = raw_pain_type.replace("_", " ").title()
    else:
        complaint = str(pain.get("complaint") or "").strip().rstrip(".")
        lowered = complaint.lower()
        if "observability" in lowered and "retrieval" in lowered:
            pain_type = "Retrieval Trace Debugging"
        elif "latency" in lowered:
            pain_type = "RAG Trace Latency Diagnostics"
        elif "evaluation gate" in lowered or "deployment" in lowered:
            pain_type = "Production Evaluation Gates"
        elif "permission" in lowered or "enterprise" in lowered:
            pain_type = "Enterprise Permission Workflows"
        elif "ci workflow" in lowered or "integrating" in lowered:
            pain_type = "CI Evaluation Workflows"
        else:
            pain_type = complaint if complaint else "Production Workflow"
    if "Tracing" in cap_name or "observability" in cap_name:
        return f"Production Debugging Layer for {pain_type}"
    if "Evaluation" in cap_name:
        return f"Regression Evaluation Workflow for {pain_type}"
    if "Enterprise" in cap_name:
        return f"Enterprise Control Layer for {pain_type}"
    if "Deployment" in cap_name:
        return f"Managed Deployment Layer for {pain_type}"
    return f"{cap_name} for {pain_type}"


class FusionGenerator:
    """Combine pain, mature capability, and optional research proof."""

    def generate(self, state: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
        pains = state.get("pain_points") or []
        capabilities = state.get("repo_capabilities") or []
        research = state.get("research_evidence") or []
        candidates: list[FusionCandidate] = []
        for pain in pains[:12]:
            for capability in capabilities[:12]:
                if not _capability_matches_pain(pain, capability):
                    continue
                related_research = _related_research(capability, research)
                evidence_ids = _evidence_ids(pain, capability)
                scores = score_fusion_candidate(pain, capability, related_research)
                pain_text = _human_pain(pain)
                title = _title(capability, pain)
                candidate = FusionCandidate(
                    fusion_id=f"fusion_{_slug(str(pain.get('pain_id') or pain.get('evidence_id') or pain.get('pain_type')))}_{_slug(str(capability.get('capability_id')))}",
                    title=title,
                    user_query_anchor=str(state.get("canonical_topic") or state.get("user_query") or ""),
                    pain=pain,
                    capability=capability,
                    research_evidence=related_research,
                    fusion_thesis=f"{capability.get('name')} from {capability.get('source_repo')} can be productized around this repeated pain: {pain_text}.",
                    why_combination_makes_sense=(
                        f"The GitHub evidence shows a user pain, while {capability.get('source_repo')} "
                        f"shows a mature capability pattern that can be adapted to the workflow."
                    ),
                    product_angle=title,
                    target_user=str(pain.get("persona") or "engineering teams adopting GitHub OSS in production"),
                    evidence_ids=evidence_ids,
                    repo_ids=[str(capability.get("source_repo"))],
                    paper_ids=[str(item.get("paper_id")) for item in related_research],
                    risks=[
                        "Fusion may be too close to an existing product if the mature repo already serves this workflow.",
                        "Paper support indicates technical feasibility, not willingness to pay.",
                    ],
                    **scores,
                )
                candidates.append(candidate)

        deduped: dict[str, FusionCandidate] = {}
        for candidate in candidates:
            key = f"{candidate.title.lower()}::{candidate.capability.get('source_repo')}"
            existing = deduped.get(key)
            if not existing or candidate.overall_score > existing.overall_score:
                deduped[key] = candidate
        return [
            candidate.model_dump()
            for candidate in sorted(deduped.values(), key=lambda item: item.overall_score, reverse=True)[:limit]
        ]


def generate_fusion_candidates(state: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
    return FusionGenerator().generate(state, limit=limit)
