"""SQLite persistence for completed graph runs."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ITEM_TABLES = {
    "repos": ("selected_repos", "repo_id"),
    "evidence_items": ("evidence_items", "evidence_id"),
    "classified_issues": ("classified_issues", "issue_id"),
    "pain_points": ("pain_points", "pain_id"),
    "pain_clusters": ("pain_clusters", "cluster_id"),
    "commercial_gaps": ("commercial_gaps", "gap_id"),
    "opportunity_cards": ("opportunity_cards", "opportunity_id"),
    "validated_cards": ("validated_cards", "opportunity_id"),
    "rejected_cards": ("rejected_cards", "opportunity_id"),
    "agent_reviews": ("agent_reviews", "opportunity_id"),
    "final_decisions": ("final_decisions", "opportunity_id"),
}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_load(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return fallback
    return json.loads(value)


def _sqlite_path(database_url: str) -> str:
    if database_url == "sqlite:///:memory:":
        return ":memory:"
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("Only sqlite:/// DATABASE_URL values are supported by the MVP store.")
    raw_path = database_url.removeprefix(prefix)
    return raw_path or "./github_opportunity_miner.db"


def _table_for_key(key: str) -> str | None:
    for table, (state_key, _) in ITEM_TABLES.items():
        if state_key == key:
            return table
    return None


class SQLiteStore:
    """Small JSON-backed SQLite store for MVP persistence.

    The schema keeps a full `state_json` for replay and duplicates key lists into
    item tables so API endpoints can query evidence, opportunities, and reports
    without reparsing every run.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.path = _sqlite_path(database_url)
        if self.path != ":memory:":
            Path(self.path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    canonical_topic TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    dynamic_search INTEGER NOT NULL DEFAULT 0,
                    search_intent_json TEXT,
                    search_plan_json TEXT,
                    state_json TEXT NOT NULL,
                    evidence_items_count INTEGER NOT NULL DEFAULT 0,
                    opportunity_cards_count INTEGER NOT NULL DEFAULT 0,
                    validated_cards_count INTEGER NOT NULL DEFAULT 0,
                    rejected_cards_count INTEGER NOT NULL DEFAULT 0,
                    errors_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            for table in ITEM_TABLES:
                conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {table} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id TEXT NOT NULL,
                        item_id TEXT,
                        item_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                    )
                    """
                )
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_run_id ON {table}(run_id)")
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_item_id ON {table}(item_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    run_id TEXT PRIMARY KEY,
                    report_markdown TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    error_text TEXT NOT NULL,
                    error_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_errors_run_id ON errors(run_id)")

    def save_run_state(self, state: dict[str, Any], *, topic: str | None = None, dynamic_search: bool = False) -> dict[str, Any]:
        run_id = str(state["run_id"])
        now = _utc_now()
        existing = self._get_run_row(run_id)
        created_at = existing["created_at"] if existing else now
        errors = state.get("errors") or []
        status = "completed_with_errors" if errors else "completed"
        topic_value = topic or state.get("user_query") or state.get("canonical_topic") or ""
        full_state = dict(state)
        full_state.setdefault("status", status)
        full_state.setdefault("created_at", created_at)
        full_state["updated_at"] = now
        full_state["dynamic_search"] = bool(dynamic_search or state.get("dynamic_search"))

        with self.connect() as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute(
                """
                INSERT INTO runs (
                    run_id, topic, canonical_topic, status, created_at, updated_at,
                    dynamic_search, search_intent_json, search_plan_json, state_json,
                    evidence_items_count, opportunity_cards_count, validated_cards_count,
                    rejected_cards_count, errors_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    topic=excluded.topic,
                    canonical_topic=excluded.canonical_topic,
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    dynamic_search=excluded.dynamic_search,
                    search_intent_json=excluded.search_intent_json,
                    search_plan_json=excluded.search_plan_json,
                    state_json=excluded.state_json,
                    evidence_items_count=excluded.evidence_items_count,
                    opportunity_cards_count=excluded.opportunity_cards_count,
                    validated_cards_count=excluded.validated_cards_count,
                    rejected_cards_count=excluded.rejected_cards_count,
                    errors_count=excluded.errors_count
                """,
                (
                    run_id,
                    str(topic_value),
                    state.get("canonical_topic"),
                    status,
                    created_at,
                    now,
                    1 if full_state["dynamic_search"] else 0,
                    _json_dump(state.get("search_intent") or {}),
                    _json_dump(state.get("search_plan") or {}),
                    _json_dump(full_state),
                    len(state.get("evidence_items") or []),
                    len(state.get("opportunity_cards") or []),
                    len(state.get("validated_cards") or []),
                    len(state.get("rejected_cards") or []),
                    len(errors),
                ),
            )
            for table in ITEM_TABLES:
                conn.execute(f"DELETE FROM {table} WHERE run_id = ?", (run_id,))
            conn.execute("DELETE FROM reports WHERE run_id = ?", (run_id,))
            conn.execute("DELETE FROM errors WHERE run_id = ?", (run_id,))

            for table, (state_key, id_key) in ITEM_TABLES.items():
                items = self._items_for_state_key(state, state_key)
                for item in items:
                    item_id = self._item_id(item, id_key)
                    conn.execute(
                        f"INSERT INTO {table} (run_id, item_id, item_json, created_at) VALUES (?, ?, ?, ?)",
                        (run_id, item_id, _json_dump(item), now),
                    )

            report_markdown = str(state.get("report_markdown") or "")
            conn.execute(
                "INSERT INTO reports (run_id, report_markdown, created_at) VALUES (?, ?, ?)",
                (run_id, report_markdown, now),
            )
            for error in errors:
                conn.execute(
                    "INSERT INTO errors (run_id, error_text, error_json, created_at) VALUES (?, ?, ?, ?)",
                    (run_id, str(error), _json_dump(error), now),
                )
        return self.get_run(run_id) or full_state

    def _get_run_row(self, run_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()

    def _items_for_state_key(self, state: dict[str, Any], state_key: str) -> list[dict[str, Any]]:
        if state_key == "selected_repos":
            repos = (state.get("selected_repos") or []) + (state.get("searched_repos") or [])
            return self._dedupe_items(repos, ["repo_id", "full_name", "url", "repo_url"])
        items = state.get(state_key) or []
        return [item for item in items if isinstance(item, dict)]

    def _dedupe_items(self, items: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for item in items:
            identity = next((str(item.get(key)) for key in keys if item.get(key)), _json_dump(item))
            if identity in seen:
                continue
            seen.add(identity)
            out.append(item)
        return out

    def _item_id(self, item: dict[str, Any], id_key: str) -> str | None:
        if item.get(id_key):
            return str(item[id_key])
        if id_key == "issue_id" and item.get("evidence_id"):
            return str(item["evidence_id"])
        if id_key == "repo_id":
            for key in ["full_name", "name_with_owner", "url", "repo_url"]:
                if item.get(key):
                    return str(item[key])
        return None

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self._get_run_row(run_id)
        if not row:
            return None
        state = _json_load(row["state_json"], {}) or {}
        state.update(
            {
                "run_id": row["run_id"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "dynamic_search": bool(row["dynamic_search"]),
            }
        )
        return state

    def get_run_summary(self, run_id: str) -> dict[str, Any] | None:
        row = self._get_run_row(run_id)
        if not row:
            return None
        return {
            "run_id": row["run_id"],
            "topic": row["topic"],
            "canonical_topic": row["canonical_topic"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "dynamic_search": bool(row["dynamic_search"]),
            "evidence_items_count": row["evidence_items_count"],
            "opportunity_cards_count": row["opportunity_cards_count"],
            "validated_cards_count": row["validated_cards_count"],
            "rejected_cards_count": row["rejected_cards_count"],
            "errors_count": row["errors_count"],
            "search_plan": _json_load(row["search_plan_json"], {}) or {},
        }

    def list_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, topic, canonical_topic, status, created_at, updated_at,
                       dynamic_search, validated_cards_count, errors_count
                FROM runs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "run_id": row["run_id"],
                "topic": row["topic"],
                "canonical_topic": row["canonical_topic"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "dynamic_search": bool(row["dynamic_search"]),
                "validated_cards_count": row["validated_cards_count"],
                "errors_count": row["errors_count"],
            }
            for row in rows
        ]

    def get_run_items(self, run_id: str, table: str) -> list[dict[str, Any]]:
        if table not in ITEM_TABLES:
            raise ValueError(f"Unsupported run item table: {table}")
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT item_json FROM {table} WHERE run_id = ? ORDER BY id ASC",
                (run_id,),
            ).fetchall()
        return [_json_load(row["item_json"], {}) for row in rows]

    def get_run_items_by_key(self, run_id: str, state_key: str) -> list[dict[str, Any]]:
        table = _table_for_key(state_key)
        if table is None:
            raise ValueError(f"Unsupported state key: {state_key}")
        return self.get_run_items(run_id, table)

    def get_report(self, run_id: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute("SELECT report_markdown FROM reports WHERE run_id = ?", (run_id,)).fetchone()
        if not row:
            return None
        return str(row["report_markdown"])

    def get_opportunity(self, opportunity_id: str) -> dict[str, Any] | None:
        for table in ["validated_cards", "opportunity_cards"]:
            with self.connect() as conn:
                row = conn.execute(
                    f"""
                    SELECT c.run_id, c.item_json
                    FROM {table} c
                    JOIN runs r ON r.run_id = c.run_id
                    WHERE c.item_id = ?
                    ORDER BY r.created_at DESC
                    LIMIT 1
                    """,
                    (opportunity_id,),
                ).fetchone()
            if row:
                item = _json_load(row["item_json"], {}) or {}
                item["run_id"] = row["run_id"]
                return item
        return None

    def get_opportunity_evidence(self, opportunity_id: str) -> list[dict[str, Any]]:
        opportunity = self.get_opportunity(opportunity_id)
        if not opportunity:
            return []
        run_id = str(opportunity["run_id"])
        evidence_ids = [str(item) for item in opportunity.get("evidence_ids", [])]
        if not evidence_ids:
            return []
        placeholders = ",".join("?" for _ in evidence_ids)
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT item_id, item_json
                FROM evidence_items
                WHERE run_id = ? AND item_id IN ({placeholders})
                """,
                (run_id, *evidence_ids),
            ).fetchall()
        by_id = {str(row["item_id"]): _json_load(row["item_json"], {}) for row in rows}
        return [by_id[evidence_id] for evidence_id in evidence_ids if evidence_id in by_id]
