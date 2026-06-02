"""Run-level persistence API."""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.memory.sqlite_store import SQLiteStore


class RunStore:
    """Facade over the SQLite MVP store.

    Keeping the graph and API code behind this facade makes it easier to swap
    SQLite for PostgreSQL later without changing endpoint contracts.
    """

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or get_settings().database_url
        self.store = SQLiteStore(self.database_url)

    def save(self, run: dict[str, Any]) -> None:
        self.save_run_state(run)

    def save_run_state(
        self,
        state: dict[str, Any],
        *,
        topic: str | None = None,
        dynamic_search: bool = False,
    ) -> dict[str, Any]:
        return self.store.save_run_state(state, topic=topic, dynamic_search=dynamic_search)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        return self.store.get_run(run_id)

    def get_summary(self, run_id: str) -> dict[str, Any] | None:
        return self.store.get_run_summary(run_id)

    def list_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return self.store.list_runs(limit=limit)

    def get_opportunities(self, run_id: str) -> list[dict[str, Any]]:
        return self.store.get_run_items_by_key(run_id, "validated_cards")

    def get_report(self, run_id: str) -> str | None:
        return self.store.get_report(run_id)

    def get_opportunity(self, opportunity_id: str) -> dict[str, Any] | None:
        return self.store.get_opportunity(opportunity_id)

    def get_opportunity_evidence(self, opportunity_id: str) -> list[dict[str, Any]]:
        return self.store.get_opportunity_evidence(opportunity_id)
