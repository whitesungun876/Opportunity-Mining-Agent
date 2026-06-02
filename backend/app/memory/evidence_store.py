"""Evidence lookup helpers backed by the run store."""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.memory.sqlite_store import SQLiteStore


class EvidenceStore:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or get_settings().database_url
        self.store = SQLiteStore(self.database_url)

    def save_many(self, evidence: list[dict]) -> None:
        """Compatibility no-op; evidence is persisted as part of a run."""
        _ = evidence
        return None

    def get_for_opportunity(self, opportunity_id: str) -> list[dict[str, Any]]:
        return self.store.get_opportunity_evidence(opportunity_id)

    def get_for_run(self, run_id: str) -> list[dict[str, Any]]:
        return self.store.get_run_items_by_key(run_id, "evidence_items")
