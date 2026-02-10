"""SQLite opportunity memory: store validate + score per theme; insert on first occurrence, update if exists."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Table: one row per opportunity theme
TABLE_SQL = """
CREATE TABLE IF NOT EXISTS opportunity_memory (
    theme TEXT PRIMARY KEY,
    run_topic TEXT,
    validation_passed INTEGER NOT NULL,
    validation_reason TEXT,
    pain_severity REAL,
    market_size REAL,
    willingness_to_pay REAL,
    competition_level REAL,
    feasibility REAL,
    total_score REAL,
    updated_at TEXT NOT NULL
);
"""


def _db_path() -> Path:
    return Path("./data/opportunity_memory.db").resolve()


def get_connection() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def theme_exists(theme: str, conn: sqlite3.Connection | None = None) -> bool:
    """Return True if theme already has a row (for Memory Novelty gate)."""
    if conn is not None:
        cur = conn.execute("SELECT 1 FROM opportunity_memory WHERE theme = ?", (theme,))
        return cur.fetchone() is not None
    with get_connection() as c:
        ensure_table(c)
        cur = c.execute("SELECT 1 FROM opportunity_memory WHERE theme = ?", (theme,))
        return cur.fetchone() is not None


def ensure_table(conn: sqlite3.Connection | None = None) -> None:
    """Create the table if it does not exist; no-op if already present."""
    if conn is not None:
        conn.execute(TABLE_SQL)
        conn.commit()
        return
    with get_connection() as c:
        c.execute(TABLE_SQL)
        c.commit()


def upsert(
    theme: str,
    *,
    run_topic: str | None = None,
    validation_passed: bool = False,
    validation_reason: str | None = None,
    pain_severity: float | None = None,
    market_size: float | None = None,
    willingness_to_pay: float | None = None,
    competition_level: float | None = None,
    feasibility: float | None = None,
    total_score: float | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Write by theme: insert on first occurrence, update if already exists."""
    now = datetime.now(timezone.utc).isoformat()
    if conn is not None:
        _do_upsert(
            conn,
            theme=theme,
            run_topic=run_topic,
            validation_passed=validation_passed,
            validation_reason=validation_reason,
            pain_severity=pain_severity,
            market_size=market_size,
            willingness_to_pay=willingness_to_pay,
            competition_level=competition_level,
            feasibility=feasibility,
            total_score=total_score,
            updated_at=now,
        )
        conn.commit()
        return
    with get_connection() as c:
        ensure_table(c)
        _do_upsert(
            c,
            theme=theme,
            run_topic=run_topic,
            validation_passed=validation_passed,
            validation_reason=validation_reason,
            pain_severity=pain_severity,
            market_size=market_size,
            willingness_to_pay=willingness_to_pay,
            competition_level=competition_level,
            feasibility=feasibility,
            total_score=total_score,
            updated_at=now,
        )
        c.commit()


def _do_upsert(
    conn: sqlite3.Connection,
    *,
    theme: str,
    run_topic: str | None,
    validation_passed: bool,
    validation_reason: str | None,
    pain_severity: float | None,
    market_size: float | None,
    willingness_to_pay: float | None,
    competition_level: float | None,
    feasibility: float | None,
    total_score: float | None,
    updated_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO opportunity_memory (
            theme, run_topic, validation_passed, validation_reason,
            pain_severity, market_size, willingness_to_pay, competition_level, feasibility, total_score, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(theme) DO UPDATE SET
            run_topic = excluded.run_topic,
            validation_passed = excluded.validation_passed,
            validation_reason = excluded.validation_reason,
            pain_severity = excluded.pain_severity,
            market_size = excluded.market_size,
            willingness_to_pay = excluded.willingness_to_pay,
            competition_level = excluded.competition_level,
            feasibility = excluded.feasibility,
            total_score = excluded.total_score,
            updated_at = excluded.updated_at
        """,
        (
            theme,
            run_topic or "",
            1 if validation_passed else 0,
            validation_reason or "",
            pain_severity,
            market_size,
            willingness_to_pay,
            competition_level,
            feasibility,
            total_score,
            updated_at,
        ),
    )
