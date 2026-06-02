"""Build a typed evidence graph from graph state artifacts."""

from __future__ import annotations

from typing import Any

from app.fusion.schemas import GraphEdge, GraphNode, OpportunityGraph


def _repo_key_from_evidence(item: dict[str, Any]) -> str:
    owner = str(item.get("repo_owner") or "").strip()
    name = str(item.get("repo_name") or "").strip()
    if owner or name:
        return f"{owner}/{name}".strip("/")
    repo_url = str(item.get("repo_url") or "")
    if "github.com/" in repo_url:
        return repo_url.split("github.com/", 1)[1].strip("/")
    return str(item.get("repo") or "unknown/unknown")


def _repo_node_id(repo_key: str) -> str:
    return f"repo:{repo_key}"


def _pain_node_id(pain: dict[str, Any]) -> str:
    return f"pain:{pain.get('pain_id') or pain.get('evidence_id') or pain.get('issue_id')}"


def _evidence_node_id(evidence_id: str) -> str:
    return f"evidence:{evidence_id}"


def _opportunity_node_id(card: dict[str, Any]) -> str:
    return f"opportunity:{card.get('opportunity_id')}"


def _gap_node_id(gap: dict[str, Any]) -> str:
    return f"gap:{gap.get('gap_id') or gap.get('cluster_id') or gap.get('commercial_gap_type')}"


def _evidence_ids(value: dict[str, Any]) -> list[str]:
    if value.get("evidence_ids"):
        return [str(item) for item in value.get("evidence_ids") or []]
    if value.get("evidence_id"):
        return [str(value["evidence_id"])]
    return []


def _add_node(nodes: dict[str, GraphNode], node: GraphNode) -> None:
    existing = nodes.get(node.node_id)
    if not existing:
        nodes[node.node_id] = node
        return
    existing.evidence_ids = list(dict.fromkeys(existing.evidence_ids + node.evidence_ids))
    existing.properties.update({key: value for key, value in node.properties.items() if value not in (None, "", [])})


def _add_edge(edges: dict[tuple[str, str, str], GraphEdge], edge: GraphEdge) -> None:
    key = (edge.source_id, edge.target_id, edge.edge_type)
    existing = edges.get(key)
    if not existing:
        edges[key] = edge
        return
    existing.confidence = max(existing.confidence, edge.confidence)
    existing.evidence_ids = list(dict.fromkeys(existing.evidence_ids + edge.evidence_ids))


class OpportunityGraphBuilder:
    """Create typed nodes and edges from current run state."""

    def build(self, state: dict[str, Any]) -> OpportunityGraph:
        nodes: dict[str, GraphNode] = {}
        edges: dict[tuple[str, str, str], GraphEdge] = {}

        evidence_by_id = {str(item.get("evidence_id")): item for item in state.get("evidence_items") or [] if item.get("evidence_id")}

        for evidence_id, item in evidence_by_id.items():
            repo_key = _repo_key_from_evidence(item)
            _add_node(
                nodes,
                GraphNode(
                    node_id=_repo_node_id(repo_key),
                    node_type="Repo",
                    label=repo_key,
                    properties={
                        "repo_url": item.get("repo_url"),
                        "repo_owner": item.get("repo_owner"),
                        "repo_name": item.get("repo_name"),
                        "is_mock": item.get("is_mock", False),
                    },
                ),
            )
            _add_node(
                nodes,
                GraphNode(
                    node_id=_evidence_node_id(evidence_id),
                    node_type="Evidence",
                    label=str(item.get("title") or evidence_id),
                    properties={
                        "source_url": item.get("source_url"),
                        "source_type": item.get("source_type"),
                        "repo": repo_key,
                    },
                    evidence_ids=[evidence_id],
                ),
            )

        pain_by_id: dict[str, dict[str, Any]] = {}
        for pain in state.get("pain_points") or []:
            pain_id = _pain_node_id(pain)
            evidence_ids = _evidence_ids(pain)
            pain_by_id[pain_id] = pain
            _add_node(
                nodes,
                GraphNode(
                    node_id=pain_id,
                    node_type="PainPoint",
                    label=str(pain.get("complaint") or pain.get("pain_type") or pain_id),
                    properties={
                        "pain_type": pain.get("pain_type"),
                        "persona": pain.get("persona"),
                        "severity": pain.get("severity"),
                        "business_signal": pain.get("business_signal"),
                    },
                    evidence_ids=evidence_ids,
                ),
            )
            for evidence_id in evidence_ids:
                evidence = evidence_by_id.get(evidence_id)
                if not evidence:
                    continue
                repo_id = _repo_node_id(_repo_key_from_evidence(evidence))
                _add_edge(
                    edges,
                    GraphEdge(
                        source_id=repo_id,
                        target_id=pain_id,
                        edge_type="repo_has_pain",
                        confidence=0.8,
                        evidence_ids=[evidence_id],
                        reason="Pain was extracted from evidence in this repo.",
                    ),
                )
                _add_edge(
                    edges,
                    GraphEdge(
                        source_id=pain_id,
                        target_id=_evidence_node_id(evidence_id),
                        edge_type="pain_supported_by_evidence",
                        confidence=0.9,
                        evidence_ids=[evidence_id],
                        reason="Evidence item supports the extracted pain point.",
                    ),
                )

        pains = list(pain_by_id.items())
        for index, (left_id, left) in enumerate(pains):
            for right_id, right in pains[index + 1 :]:
                if left.get("pain_type") and left.get("pain_type") == right.get("pain_type"):
                    _add_edge(
                        edges,
                        GraphEdge(
                            source_id=left_id,
                            target_id=right_id,
                            edge_type="pain_similar_to_pain",
                            confidence=0.65,
                            evidence_ids=list(dict.fromkeys(_evidence_ids(left) + _evidence_ids(right))),
                            reason="Pain points share a pain_type.",
                        ),
                    )

        for gap in state.get("commercial_gaps") or []:
            gap_id = _gap_node_id(gap)
            evidence_ids = _evidence_ids(gap)
            _add_node(
                nodes,
                GraphNode(
                    node_id=gap_id,
                    node_type="CommercialGap",
                    label=str(gap.get("commercial_gap_type") or gap.get("gap_summary") or gap_id),
                    properties={
                        "best_product_form": gap.get("best_product_form"),
                        "migration_cost": gap.get("migration_cost"),
                        "confidence": gap.get("confidence"),
                    },
                    evidence_ids=evidence_ids,
                ),
            )
            for pain_id, pain in pain_by_id.items():
                overlap = set(evidence_ids).intersection(_evidence_ids(pain))
                if overlap:
                    _add_edge(
                        edges,
                        GraphEdge(
                            source_id=pain_id,
                            target_id=gap_id,
                            edge_type="pain_has_commercial_gap",
                            confidence=0.75,
                            evidence_ids=sorted(overlap),
                            reason="Commercial gap references evidence from this pain.",
                        ),
                    )

        for card in (state.get("validated_cards") or state.get("opportunity_cards") or []):
            opportunity_id = _opportunity_node_id(card)
            evidence_ids = _evidence_ids(card)
            _add_node(
                nodes,
                GraphNode(
                    node_id=opportunity_id,
                    node_type="Opportunity",
                    label=str(card.get("title") or card.get("opportunity_id")),
                    properties={
                        "product_form": card.get("product_form") or card.get("best_product_form"),
                        "migration_cost": card.get("migration_cost"),
                        "weak_card": card.get("weak_card", False),
                    },
                    evidence_ids=evidence_ids,
                ),
            )
            for evidence_id in evidence_ids:
                if evidence_id in evidence_by_id:
                    _add_edge(
                        edges,
                        GraphEdge(
                            source_id=opportunity_id,
                            target_id=_evidence_node_id(evidence_id),
                            edge_type="opportunity_supported_by_evidence",
                            confidence=0.85,
                            evidence_ids=[evidence_id],
                            reason="Opportunity card cites this evidence.",
                        ),
                    )
            for pain_id, pain in pain_by_id.items():
                overlap = set(evidence_ids).intersection(_evidence_ids(pain))
                if overlap:
                    _add_edge(
                        edges,
                        GraphEdge(
                            source_id=opportunity_id,
                            target_id=pain_id,
                            edge_type="opportunity_combines",
                            confidence=0.72,
                            evidence_ids=sorted(overlap),
                            reason="Opportunity combines product angle with this pain.",
                        ),
                    )

        return OpportunityGraph(nodes=list(nodes.values()), edges=list(edges.values()))


def build_opportunity_graph(state: dict[str, Any]) -> dict[str, Any]:
    """Return a serializable typed evidence graph."""
    return OpportunityGraphBuilder().build(state).model_dump_graph()
