"""Opportunities API router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.memory.run_store import RunStore


router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _store() -> RunStore:
    return RunStore()


@router.get("/{opportunity_id}")
def get_opportunity(opportunity_id: str) -> dict:
    opportunity = _store().get_opportunity(opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="opportunity not found")
    return opportunity


@router.get("/{opportunity_id}/evidence")
def get_opportunity_evidence(opportunity_id: str) -> dict:
    opportunity = _store().get_opportunity(opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="opportunity not found")
    evidence = _store().get_opportunity_evidence(opportunity_id)
    return {"opportunity_id": opportunity_id, "count": len(evidence), "evidence_items": evidence}
