"""Skill execution facade."""

from __future__ import annotations

from typing import Callable, Any

from app.harness.tool_runner import ToolRunner
from app.skills.registry import DEFAULT_REGISTRY


class SkillRunner:
    """Run registered skills through the harness ToolRunner."""

    def __init__(self, tool_runner: ToolRunner | None = None) -> None:
        self.tool_runner = tool_runner or ToolRunner(mock_mode=True)
        self.registry = DEFAULT_REGISTRY

    def run(self, skill_name: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        spec = self.registry.get(skill_name)
        return self.tool_runner.run(
            fn,
            *args,
            timeout_seconds=spec.timeout_seconds,
            retry_limit=spec.retry_limit,
            node_name=skill_name,
            **kwargs,
        )
