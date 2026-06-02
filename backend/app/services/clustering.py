"""Pain-point clustering and deduplication services."""

from __future__ import annotations

from collections import defaultdict
import math
import re
from typing import Any

from app.services.embedding_client import EmbeddingClient


PAIN_TYPE_ALIASES = {
    "production_deployment_blocker": "deployment_complexity",
    "deployment_blocker": "deployment_complexity",
    "deployment": "deployment_complexity",
    "observability_debugging_gap": "observability_gap",
    "debugging_gap": "observability_gap",
    "eval_gap": "evaluation_gap",
    "security_gap": "enterprise_security_gap",
    "auth_gap": "permission_gap",
}


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    denom = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(y * y for y in right))
    if denom == 0:
        return 0.0
    return sum(x * y for x, y in zip(left, right)) / denom


def _pain_type(pain: dict[str, Any]) -> str:
    raw = str(pain.get("pain_type") or pain.get("topic") or "unclear").strip().lower()
    return PAIN_TYPE_ALIASES.get(raw, raw or "unclear")


def _pain_text(pain: dict[str, Any]) -> str:
    return " ".join(
        str(pain.get(key) or "")
        for key in ["pain_type", "complaint", "context", "business_signal", "supporting_quote"]
    ).strip()


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9_+-]*", text.lower()))


def _cluster_theme(pains: list[dict[str, Any]], pain_type: str) -> str:
    for pain in pains:
        complaint = str(pain.get("complaint") or "").strip()
        if complaint:
            return complaint[:120]
    return pain_type.replace("_", " ").title()


def _repo_count(evidence_items: list[dict[str, Any]], evidence_ids: list[str]) -> int:
    by_id = {str(item.get("evidence_id")): item for item in evidence_items}
    repos = set()
    for evidence_id in evidence_ids:
        item = by_id.get(str(evidence_id))
        if not item:
            continue
        repo = item.get("repo") or f"{item.get('repo_owner')}/{item.get('repo_name')}"
        if repo and repo != "/":
            repos.add(str(repo))
    return len(repos)


def _severity(pains: list[dict[str, Any]]) -> float:
    scores = []
    for pain in pains:
        try:
            scores.append(float(pain.get("severity") or 0.5))
        except (TypeError, ValueError):
            scores.append(0.5)
    return round(sum(scores) / max(1, len(scores)), 3)


def _cluster_from_pains(cluster_id: str, pains: list[dict[str, Any]], evidence_items: list[dict[str, Any]]) -> dict[str, Any]:
    pain_type = _pain_type(pains[0]) if pains else "unclear"
    evidence_ids = list(dict.fromkeys(str(pain.get("evidence_id") or "") for pain in pains if pain.get("evidence_id")))
    quotes = [
        str(pain.get("supporting_quote") or pain.get("complaint") or "").strip()
        for pain in pains
        if str(pain.get("supporting_quote") or pain.get("complaint") or "").strip()
    ][:3]
    theme = _cluster_theme(pains, pain_type)
    return {
        "cluster_id": cluster_id,
        "topic": pain_type.replace("_", " "),
        "theme": theme,
        "pain_type": pain_type,
        "pain_ids": [str(pain.get("pain_id") or f"pain_{idx}") for idx, pain in enumerate(pains, start=1)],
        "evidence_ids": evidence_ids,
        "evidence_count": len(evidence_ids),
        "repo_count": _repo_count(evidence_items, evidence_ids),
        "severity_score": _severity(pains),
        "repetition_score": round(min(1.0, len(evidence_ids) / 5), 3),
        "summary": f"{len(pains)} related pains around {theme}",
        "example_quotes": quotes,
    }


def _merge_cluster_group(clusters: list[dict[str, Any]], evidence_items: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge sparse same-type clusters while preserving evidence lineage."""
    ordered = sorted(
        clusters,
        key=lambda item: (
            int(item.get("evidence_count") or len(item.get("evidence_ids") or [])),
            float(item.get("severity_score") or 0),
        ),
        reverse=True,
    )
    base = ordered[0]
    pain_ids: list[str] = []
    evidence_ids: list[str] = []
    quotes: list[str] = []
    themes: list[str] = []
    merged_from: list[str] = []
    severity_scores: list[float] = []

    for cluster in ordered:
        pain_ids.extend(str(item) for item in cluster.get("pain_ids") or [])
        evidence_ids.extend(str(item) for item in cluster.get("evidence_ids") or [])
        quotes.extend(str(item) for item in cluster.get("example_quotes") or [] if str(item).strip())
        theme = str(cluster.get("theme") or "").strip()
        if theme:
            themes.append(theme)
        merged_from.extend(str(item) for item in cluster.get("merged_from") or [cluster.get("cluster_id")])
        try:
            severity_scores.append(float(cluster.get("severity_score") or 0))
        except (TypeError, ValueError):
            severity_scores.append(0)

    unique_evidence_ids = list(dict.fromkeys(evidence_ids))
    unique_themes = list(dict.fromkeys(themes))[:3]
    pain_type = str(base.get("pain_type") or "unclear")
    readable_type = pain_type.replace("_", " ")
    summary_theme = "; ".join(unique_themes) if unique_themes else readable_type

    return {
        **base,
        "pain_ids": list(dict.fromkeys(pain_ids)),
        "evidence_ids": unique_evidence_ids,
        "evidence_count": len(unique_evidence_ids),
        "repo_count": _repo_count(evidence_items, unique_evidence_ids),
        "severity_score": round(max(severity_scores or [0.5]), 3),
        "repetition_score": round(min(1.0, len(unique_evidence_ids) / 5), 3),
        "summary": f"Merged {len(set(pain_ids))} related pains around {summary_theme}",
        "example_quotes": list(dict.fromkeys(quotes))[:5],
        "merged_from": list(dict.fromkeys(merged_from)),
        "theme": unique_themes[0] if unique_themes else str(base.get("theme") or readable_type.title()),
    }


def merge_sparse_same_type_clusters(
    clusters: list[dict[str, Any]],
    *,
    evidence_items: list[dict[str, Any]] | None = None,
    min_evidence_to_merge: int = 3,
) -> list[dict[str, Any]]:
    """Consolidate fragmented same-type clusters so repeated real pains can pass the gate.

    Real LLM pain extraction often produces specific complaints. With deterministic
    embedding fallback, those complaints can become many one-evidence clusters even
    when they clearly share the same production pain type. This keeps strong clusters
    intact and only merges sparse clusters when their combined evidence is sufficient.
    """
    if len(clusters) <= 1:
        return clusters
    evidence_items = evidence_items or []
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cluster in clusters:
        groups[str(cluster.get("pain_type") or "unclear")].append(cluster)

    consolidated: list[dict[str, Any]] = []
    for _pain_type_key, group in groups.items():
        if len(group) == 1:
            consolidated.extend(group)
            continue

        strong = [
            cluster
            for cluster in group
            if int(cluster.get("evidence_count") or len(cluster.get("evidence_ids") or [])) >= min_evidence_to_merge
        ]
        sparse = [
            cluster
            for cluster in group
            if int(cluster.get("evidence_count") or len(cluster.get("evidence_ids") or [])) < min_evidence_to_merge
        ]
        consolidated.extend(strong)

        sparse_evidence_ids = list(
            dict.fromkeys(
                str(evidence_id)
                for cluster in sparse
                for evidence_id in (cluster.get("evidence_ids") or [])
                if evidence_id
            )
        )
        if len(sparse_evidence_ids) >= min_evidence_to_merge:
            consolidated.append(_merge_cluster_group(sparse, evidence_items))
        else:
            consolidated.extend(sparse)

    consolidated.sort(
        key=lambda item: (
            int(item.get("evidence_count") or len(item.get("evidence_ids") or [])),
            float(item.get("repetition_score") or 0),
            float(item.get("severity_score") or 0),
        ),
        reverse=True,
    )
    return consolidated


def _should_merge_clusters(left: dict[str, Any], right: dict[str, Any], embeddings: dict[str, list[float]]) -> bool:
    evidence_overlap = len(set(left.get("evidence_ids") or []) & set(right.get("evidence_ids") or []))
    if evidence_overlap:
        return True
    left_tokens = _tokens(f"{left.get('theme', '')} {left.get('summary', '')}")
    right_tokens = _tokens(f"{right.get('theme', '')} {right.get('summary', '')}")
    jaccard = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
    if jaccard >= 0.45:
        return True
    left_vec = embeddings.get(str(left.get("cluster_id")), [])
    right_vec = embeddings.get(str(right.get("cluster_id")), [])
    return cosine_similarity(left_vec, right_vec) >= 0.82


def dedupe_pain_clusters(clusters: list[dict[str, Any]], *, embedding_client: EmbeddingClient | None = None) -> list[dict[str, Any]]:
    """Merge highly similar clusters and preserve all evidence ids."""
    if len(clusters) <= 1:
        return clusters
    client = embedding_client or EmbeddingClient()
    texts = [f"{cluster.get('pain_type')} {cluster.get('theme')} {cluster.get('summary')}" for cluster in clusters]
    vectors = client.embed_batch(texts)
    embeddings = {str(cluster.get("cluster_id")): vector for cluster, vector in zip(clusters, vectors)}
    merged: list[dict[str, Any]] = []
    consumed: set[int] = set()
    for idx, cluster in enumerate(clusters):
        if idx in consumed:
            continue
        current = {**cluster, "merged_from": list(cluster.get("merged_from") or [cluster.get("cluster_id")])}
        for other_idx in range(idx + 1, len(clusters)):
            if other_idx in consumed:
                continue
            other = clusters[other_idx]
            if not _should_merge_clusters(current, other, embeddings):
                continue
            consumed.add(other_idx)
            current["pain_ids"] = list(dict.fromkeys((current.get("pain_ids") or []) + (other.get("pain_ids") or [])))
            current["evidence_ids"] = list(dict.fromkeys((current.get("evidence_ids") or []) + (other.get("evidence_ids") or [])))
            current["evidence_count"] = len(current["evidence_ids"])
            current["repo_count"] = max(int(current.get("repo_count") or 0), int(other.get("repo_count") or 0))
            current["severity_score"] = round(max(float(current.get("severity_score") or 0), float(other.get("severity_score") or 0)), 3)
            current["repetition_score"] = round(min(1.0, len(current["evidence_ids"]) / 5), 3)
            current["example_quotes"] = list(dict.fromkeys((current.get("example_quotes") or []) + (other.get("example_quotes") or [])))[:5]
            current["summary"] = f"Merged {len(current['pain_ids'])} related pains around {current.get('theme')}"
            current["merged_from"] = list(dict.fromkeys(current["merged_from"] + (other.get("merged_from") or [other.get("cluster_id")])))
        merged.append(current)
    return merged


def cluster_pain_points(
    pain_points: list[dict[str, Any]],
    *,
    evidence_items: list[dict[str, Any]] | None = None,
    embedding_client: EmbeddingClient | None = None,
    similarity_threshold: float = 0.76,
) -> list[dict[str, Any]]:
    """Cluster pain points by type and embedding similarity."""
    if not pain_points:
        return []
    evidence_items = evidence_items or []
    client = embedding_client or EmbeddingClient()
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pain in pain_points:
        groups[_pain_type(pain)].append(pain)

    clusters: list[dict[str, Any]] = []
    cluster_counter = 1
    for pain_type, pains in groups.items():
        texts = [_pain_text(pain) for pain in pains]
        vectors = client.embed_batch(texts)
        local_clusters: list[dict[str, Any]] = []
        for pain, vector in zip(pains, vectors):
            assigned = False
            for local in local_clusters:
                if cosine_similarity(vector, local["centroid"]) >= similarity_threshold:
                    local["pains"].append(pain)
                    count = len(local["pains"])
                    local["centroid"] = [
                        ((count - 1) * old + new) / count
                        for old, new in zip(local["centroid"], vector)
                    ]
                    assigned = True
                    break
            if not assigned:
                local_clusters.append({"centroid": vector, "pains": [pain], "pain_type": pain_type})

        for local in local_clusters:
            clusters.append(_cluster_from_pains(f"cluster_{cluster_counter}", local["pains"], evidence_items))
            cluster_counter += 1
    deduped = dedupe_pain_clusters(clusters, embedding_client=client)
    return merge_sparse_same_type_clusters(deduped, evidence_items=evidence_items)
