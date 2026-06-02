"""Pain point models."""

from __future__ import annotations

from pydantic import BaseModel


class PainPoint(BaseModel):
    pain_id: str
    complaint: str
    evidence_ids: list[str]
