"""Run API router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from uuid import uuid4

from app.graph.main_graph import run_graph
from app.memory.run_store import RunStore
from app.models.run import RunCreateRequest, RunCreateResponse, RunPreflightRequest, RunPreflightResponse
from app.services.preflight import run_preflight
from app.services.preflight_cache import get_preflight_initial_state
from app.services.public_beta import PublicBetaGuard
from app.services.run_jobs import run_job_manager


router = APIRouter(prefix="/runs", tags=["runs"])


def _store() -> RunStore:
    return RunStore()


@router.post("", response_model=RunCreateResponse)
def create_run(request: RunCreateRequest, http_request: Request) -> dict[str, str]:
    """Start a graph run asynchronously and return immediately."""
    PublicBetaGuard().guard_run(http_request, request.invite_code, request.preflight_id)
    run_id = str(uuid4())
    initial_state = get_preflight_initial_state(request.preflight_id)
    if initial_state is not None:
        initial_state["preflight_id"] = request.preflight_id
        initial_state["warm_start_evidence"] = True
    job = run_job_manager.submit(
        run_id=run_id,
        topic=request.topic,
        dynamic_search=request.dynamic_search,
        run_mode=request.run_mode,
        initial_state=initial_state,
        runner=run_graph,
    )
    return {"run_id": job.run_id, "status": job.status}


@router.post("/preflight", response_model=RunPreflightResponse)
def preflight_run(request: RunPreflightRequest, http_request: Request) -> dict:
    """Cheaply estimate opportunity signal before running the full graph."""
    PublicBetaGuard().guard_preflight(http_request, request.invite_code)
    return run_preflight(request.topic, dynamic_search=request.dynamic_search)


@router.get("")
def list_runs(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    return {"runs": _store().list_runs(limit=limit)}


@router.get("/{run_id}/status")
def get_run_status(run_id: str) -> dict:
    job = run_job_manager.get(run_id)
    if job is not None:
        return job.to_dict()

    summary = _store().get_summary(run_id)
    if summary is not None:
        return {
            "run_id": run_id,
            "topic": summary["topic"],
            "dynamic_search": summary["dynamic_search"],
            "status": summary["status"],
            "progress": 100,
            "current_node": "complete",
            "message": "Run complete",
            "created_at": summary["created_at"],
            "updated_at": summary["updated_at"],
            "error": None,
            "errors": [],
        }

    raise HTTPException(status_code=404, detail="run not found")


@router.get("/{run_id}")
def get_run(run_id: str) -> dict:
    state = _store().get_run(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="run not found")
    return state


@router.get("/{run_id}/summary")
def get_run_summary(run_id: str) -> dict:
    summary = _store().get_summary(run_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="run not found")
    return summary


@router.get("/{run_id}/opportunities")
def get_run_opportunities(run_id: str) -> dict:
    if _store().get_summary(run_id) is None:
        raise HTTPException(status_code=404, detail="run not found")
    opportunities = _store().get_opportunities(run_id)
    return {"run_id": run_id, "count": len(opportunities), "opportunities": opportunities}


@router.get("/{run_id}/report")
def get_run_report(run_id: str) -> dict:
    report = _store().get_report(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {"run_id": run_id, "report_markdown": report}
