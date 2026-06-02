"""Evidence models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Evidence(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    evidence_id: str
    run_id: str | None = None
    repo_id: str | None = None
    repo_owner: str | None = None
    repo_name: str | None = None
    repo_url: str | None = None
    source_type: str | None = None
    source_url: str = Field(default="", alias="url")
    title: str = ""
    body: str = ""
    comments: list[dict[str, Any]] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    author_login: str | None = None
    comment_count: int = 0
    reaction_count: int = 0
    state: str | None = None
    created_at: str | None = None
    collected_at: str | None = None
    is_mock: bool = False
    text_hash: str | None = None

    @property
    def url(self) -> str:
        return self.source_url

    @property
    def quote(self) -> str:
        return self.body[:240]
