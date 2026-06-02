"""Central SkillRegistry for graph nodes and harness execution."""

from __future__ import annotations

from app.skills.base import SkillSpec


class SkillRegistry:
    """In-memory skill registry for the MVP."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillSpec] = {}

    def register(self, spec: SkillSpec) -> None:
        self._skills[spec.name] = spec

    def get(self, name: str) -> SkillSpec:
        if name not in self._skills:
            raise KeyError(f"Skill not registered: {name}")
        return self._skills[name]

    def list(self) -> list[SkillSpec]:
        return list(self._skills.values())


def build_default_registry() -> SkillRegistry:
    """Register mock-first GitHub opportunity mining skills."""
    registry = SkillRegistry()
    for spec in [
        SkillSpec(
            name="github_repo_search_skill",
            description="Search GitHub repositories related to a topic.",
            input_schema={"topic": "str", "queries": "list[str]"},
            output_schema={"repos": "list[dict]"},
            cost_level="low",
            requires_network=False,
        ),
        SkillSpec(
            name="github_issue_collect_skill",
            description="Collect issues from selected repositories.",
            input_schema={"repos": "list[dict]"},
            output_schema={"issues": "list[dict]"},
            cost_level="medium",
            requires_network=False,
        ),
        SkillSpec(
            name="github_discussion_collect_skill",
            description="Collect discussions from selected repositories.",
            input_schema={"repos": "list[dict]"},
            output_schema={"discussions": "list[dict]"},
            cost_level="medium",
            requires_network=False,
        ),
        SkillSpec(
            name="issue_classify_skill",
            description="Classify low-value support issues vs production pain signals.",
            input_schema={"issues": "list[dict]"},
            output_schema={"classified_issues": "list[dict]"},
            cost_level="low",
            requires_network=False,
        ),
        SkillSpec(
            name="pain_extract_skill",
            description="Extract production pain points from high-value GitHub issues.",
            input_schema={"high_value_issues": "list[dict]"},
            output_schema={"pain_points": "list[dict]"},
            cost_level="medium",
            requires_network=False,
        ),
        SkillSpec(
            name="embedding_cluster_skill",
            description="Cluster repeated pain points into opportunity themes.",
            input_schema={"pain_points": "list[dict]"},
            output_schema={"pain_clusters": "list[dict]"},
            cost_level="medium",
            requires_network=False,
        ),
    ]:
        registry.register(spec)
    return registry


DEFAULT_REGISTRY = build_default_registry()
