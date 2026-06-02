"""Seed user model placeholder."""

from __future__ import annotations

from pydantic import BaseModel


class SeedUser(BaseModel):
    persona: str
    workflow: str
    pain: str
