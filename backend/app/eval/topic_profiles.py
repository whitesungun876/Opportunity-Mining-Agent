"""YAML-backed benchmark profiles for live quality evaluation.

These profiles are not the product search path. They pin repeatable benchmark
queries so changes to the planner, prompts, and validators can be compared.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


DEFAULT_PROFILE_PATH = Path(__file__).resolve().with_name("topic_profiles.yaml")


class TopicProfile(BaseModel):
    profile_id: str
    label: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    queries: list[str]
    quality_keywords: list[str] = Field(default_factory=list)
    default_per_query: int = 5
    default_max_issues: int = 24

    def render_queries(self, topic: str) -> list[str]:
        return [query.format(topic=topic) for query in self.queries]


def load_profile_config(path: str | Path | None = None) -> dict[str, Any]:
    profile_path = Path(path) if path else DEFAULT_PROFILE_PATH
    with profile_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid topic profile file: {profile_path}")
    return data


def list_profiles(path: str | Path | None = None) -> dict[str, TopicProfile]:
    data = load_profile_config(path)
    profiles: dict[str, TopicProfile] = {}
    for profile_id, raw in (data.get("profiles") or {}).items():
        profiles[profile_id] = TopicProfile(profile_id=profile_id, **raw)
    generic = data.get("generic")
    if generic:
        profiles["generic"] = TopicProfile(
            profile_id="generic",
            label="Generic",
            aliases=[],
            **generic,
        )
    return profiles


def list_profile_summaries(path: str | Path | None = None) -> list[dict[str, Any]]:
    return [
        {
            "profile_id": profile.profile_id,
            "label": profile.label,
            "aliases": profile.aliases,
            "description": profile.description,
            "query_count": len(profile.queries),
            "default_per_query": profile.default_per_query,
            "default_max_issues": profile.default_max_issues,
        }
        for profile in list_profiles(path).values()
    ]


def resolve_profile(
    *,
    topic: str,
    profile_id: str | None = None,
    path: str | Path | None = None,
) -> TopicProfile:
    data = load_profile_config(path)
    profiles = list_profiles(path)
    if profile_id:
        if profile_id not in profiles:
            raise ValueError(f"Unknown topic profile: {profile_id}")
        return profiles[profile_id]

    normalized_topic = topic.strip().lower()
    for profile in profiles.values():
        aliases = [alias.lower() for alias in profile.aliases]
        if normalized_topic == profile.profile_id.lower() or normalized_topic in aliases:
            return profile

    default_profile = data.get("default_profile")
    if default_profile and normalized_topic in {"", "default"} and default_profile in profiles:
        return profiles[default_profile]
    return profiles["generic"]
