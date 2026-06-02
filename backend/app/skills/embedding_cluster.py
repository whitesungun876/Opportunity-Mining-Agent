"""Mock embedding clustering skill."""

from __future__ import annotations


def cluster_pains(pain_points: list[dict]) -> list[dict]:
    buckets = {
        "Production evaluation and regression workflow": ["evaluation", "regression", "trace"],
        "Enterprise deployment and permission gaps": ["permission", "enterprise", "security"],
        "Integration and CI workflow friction": ["integrating", "workflow", "CI"],
    }
    clusters: list[dict] = []
    for idx, (theme, terms) in enumerate(buckets.items(), start=1):
        matched = [
            pain
            for pain in pain_points
            if any(term.lower() in (pain.get("complaint", "") + pain.get("cause", "")).lower() for term in terms)
        ]
        if not matched:
            matched = pain_points[idx - 1 : idx + 2]
        evidence_ids = []
        for pain in matched:
            evidence_ids.extend(pain.get("evidence_ids", []))
        clusters.append(
            {
                "cluster_id": f"cluster_{idx}",
                "theme": theme,
                "pain_ids": [pain["pain_id"] for pain in matched],
                "evidence_ids": list(dict.fromkeys(evidence_ids))[:8],
                "sample_size": len(matched),
                "confidence": 0.78,
            }
        )
    return clusters
