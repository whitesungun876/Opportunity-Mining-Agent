"""Repository models."""

from __future__ import annotations

from pydantic import BaseModel


class Repo(BaseModel):
    repo_id: str
    full_name: str
    url: str
    stars: int = 0
