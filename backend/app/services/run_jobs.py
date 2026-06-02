"""In-process async run job manager for the local MVP."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Callable

from app.memory.run_store import RunStore


GraphRunner = Callable[..., dict[str, Any]]


NODE_PROGRESS: dict[str, tuple[int, str]] = {
    "query_rewrite": (5, "Rewriting query"),
    "query_scope_detect": (8, "Detecting query scope"),
    "intent_detect": (12, "Detecting search intent"),
    "search_plan_generate": (16, "Planning search strategy"),
    "github_search_orchestrator": (30, "Searching GitHub and collecting evidence"),
    "evidence_quality_rank": (38, "Ranking evidence quality"),
    "adaptive_query_expand": (42, "Expanding search queries"),
    "issue_classify": (50, "Classifying issues"),
    "pain_extract": (58, "Extracting production pain"),
    "topic_cluster": (64, "Clustering repeated pains"),
    "commercial_gap": (70, "Detecting commercial gaps"),
    "opportunity_generate": (76, "Generating opportunity cards"),
    "opportunity_dedup": (80, "Deduplicating opportunities"),
    "evidence_validate": (84, "Validating evidence"),
    "evidence_graph_build": (88, "Building evidence graph"),
    "capability_discover": (91, "Discovering reusable capabilities"),
    "research_retrieve": (93, "Retrieving technical research support"),
    "fusion_generate": (95, "Generating fusion candidates"),
    "fusion_validate": (96, "Validating fusion candidates"),
    "debate": (97, "Running structured review"),
    "buyer_hypothesis": (97, "Building buyer hypothesis"),
    "wtp_signal_detect": (97, "Detecting willingness-to-pay signals"),
    "competitor_scan": (98, "Scanning alternatives"),
    "outreach_targets": (98, "Finding first users to contact"),
    "validation_plan": (98, "Writing validation plan"),
    "final_judge": (98, "Making final decisions"),
    "startup_memo": (99, "Writing startup memo"),
    "report_write": (99, "Writing report"),
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _retarget_cached_state(state: dict[str, Any], run_id: str) -> dict[str, Any]:
    out = dict(state)
    for key in ["evidence_items", "evidence_pool", "ranked_evidence_items"]:
        items = out.get(key)
        if isinstance(items, list):
            out[key] = [{**item, "run_id": run_id} if isinstance(item, dict) else item for item in items]
    return out


@dataclass
class RunJob:
    run_id: str
    topic: str
    dynamic_search: bool
    run_mode: str = "standard"
    status: str = "queued"
    progress: int = 1
    current_node: str | None = None
    message: str = "Queued"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    error: str | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "topic": self.topic,
            "dynamic_search": self.dynamic_search,
            "run_mode": self.run_mode,
            "status": self.status,
            "progress": self.progress,
            "current_node": self.current_node,
            "message": self.message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
            "errors": self.errors,
        }


class RunJobManager:
    """Small in-memory job registry.

    This is intentionally local-process only. The endpoint contract can later be
    backed by Celery, RQ, Dramatiq, or another worker without changing the UI.
    """

    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="run-job")
        self._jobs: dict[str, RunJob] = {}
        self._lock = Lock()

    def submit(
        self,
        *,
        run_id: str,
        topic: str,
        dynamic_search: bool,
        runner: GraphRunner,
        run_mode: str = "standard",
        initial_state: dict[str, Any] | None = None,
    ) -> RunJob:
        job = RunJob(run_id=run_id, topic=topic, dynamic_search=dynamic_search, run_mode=run_mode)
        with self._lock:
            self._jobs[run_id] = job
        self._executor.submit(self._run, job, runner, initial_state or {})
        return job

    def get(self, run_id: str) -> RunJob | None:
        with self._lock:
            return self._jobs.get(run_id)

    def _update(self, run_id: str, **fields: Any) -> None:
        with self._lock:
            job = self._jobs.get(run_id)
            if job is None:
                return
            for key, value in fields.items():
                setattr(job, key, value)
            job.updated_at = _now()

    def _progress_callback(self, run_id: str) -> Callable[[str, str], None]:
        def callback(node_name: str, event: str = "started") -> None:
            progress, message = NODE_PROGRESS.get(node_name, (20, f"Running {node_name}"))
            if event == "started":
                progress = max(2, progress - 2)
            self._update(
                run_id,
                status="running",
                current_node=node_name,
                progress=progress,
                message=message,
            )

        return callback

    def _run(self, job: RunJob, runner: GraphRunner, initial_state: dict[str, Any]) -> None:
        self._update(job.run_id, status="running", progress=2, message="Starting run")
        try:
            initial_state = _retarget_cached_state(initial_state, job.run_id)
            graph_initial_state = {
                **initial_state,
                "run_id": job.run_id,
                "dynamic_search": job.dynamic_search,
                "run_mode": job.run_mode,
                "_progress_callback": self._progress_callback(job.run_id),
            }
            state = runner(
                job.topic,
                initial_state=graph_initial_state,
            )
            state["run_id"] = job.run_id
            saved = RunStore().save_run_state(state, topic=job.topic, dynamic_search=job.dynamic_search)
            self._update(
                job.run_id,
                status=saved.get("status", "completed"),
                progress=100,
                current_node="complete",
                message="Run complete",
                errors=saved.get("errors") or [],
            )
        except Exception as exc:  # pragma: no cover - exercised through API behavior.
            error = f"{type(exc).__name__}: {exc}"
            self._update(
                job.run_id,
                status="failed",
                progress=100,
                current_node="failed",
                message="Run failed",
                error=error,
                errors=[error],
            )


run_job_manager = RunJobManager()
