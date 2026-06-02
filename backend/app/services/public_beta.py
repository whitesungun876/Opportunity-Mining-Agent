"""Public beta access guard and lightweight quota tracking."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, Request

from app.config import Settings, get_settings


def _sqlite_path(database_url: str) -> str:
    if database_url == "sqlite:///:memory:":
        return ":memory:"
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        # The MVP quota store is SQLite-backed. Postgres deployments should
        # replace this with a shared rate-limit store such as Redis or Postgres.
        return "./github_opportunity_miner.db"
    return database_url.removeprefix(prefix) or "./github_opportunity_miner.db"


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    raw = forwarded.split(",", 1)[0].strip() or (request.client.host if request.client else "unknown")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BetaLimit:
    action: str
    daily_limit: int


class PublicBetaGuard:
    """Protect public demos from unbounded API and LLM spend."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.path = _sqlite_path(self.settings.database_url)
        if self.path != ":memory:":
            Path(self.path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS public_beta_usage (
                    usage_date TEXT NOT NULL,
                    client_key TEXT NOT NULL,
                    action TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (usage_date, client_key, action)
                )
                """
            )

    def _check_invite(self, invite_code: str | None) -> None:
        allowed = set(self.settings.public_beta_invite_codes)
        if not allowed:
            raise HTTPException(
                status_code=503,
                detail="Public beta is enabled, but no invite codes are configured.",
            )
        if not invite_code or invite_code.strip() not in allowed:
            raise HTTPException(status_code=403, detail="A valid invite code is required for the public beta.")

    def _consume(self, request: Request, limit: BetaLimit) -> None:
        client_key = _client_key(request)
        usage_date = _today()
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT count FROM public_beta_usage
                WHERE usage_date = ? AND client_key = ? AND action = ?
                """,
                (usage_date, client_key, limit.action),
            ).fetchone()
            current = int(row["count"]) if row else 0
            if current >= limit.daily_limit:
                raise HTTPException(
                    status_code=429,
                    detail=f"Daily {limit.action} limit reached for the public beta. Try again tomorrow.",
                )
            conn.execute(
                """
                INSERT INTO public_beta_usage (usage_date, client_key, action, count, updated_at)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(usage_date, client_key, action) DO UPDATE SET
                    count = count + 1,
                    updated_at = excluded.updated_at
                """,
                (usage_date, client_key, limit.action, now),
            )

    def guard_preflight(self, request: Request, invite_code: str | None) -> None:
        if not self.settings.public_beta_enabled:
            return
        self._check_invite(invite_code)
        self._consume(
            request,
            BetaLimit(action="preflight", daily_limit=self.settings.public_beta_daily_preflight_limit),
        )

    def guard_run(self, request: Request, invite_code: str | None, preflight_id: str | None) -> None:
        if not self.settings.public_beta_enabled:
            return
        self._check_invite(invite_code)
        if self.settings.public_beta_require_preflight and not preflight_id:
            raise HTTPException(status_code=400, detail="Public beta runs require a successful preflight check.")
        self._consume(
            request,
            BetaLimit(action="run", daily_limit=self.settings.public_beta_daily_run_limit),
        )
