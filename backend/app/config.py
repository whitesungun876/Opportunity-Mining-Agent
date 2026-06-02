"""Application configuration for mock-first MVP."""

from __future__ import annotations

from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    app_name: str = "GitHub Opportunity Miner"
    mock_mode: bool = True
    sqlite_path: str = "./data/opportunity_miner.db"
    database_url: str = "sqlite:///./github_opportunity_miner.db"
    github_graphql_url: str = "https://api.github.com/graphql"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    github_token: str | None = None
    default_model: str = "mock-llm"
    validation_mode: str = "strict"
    max_llm_concurrency: int = 4
    max_github_concurrency: int = 3
    llm_cache_enabled: bool = True
    llm_cache_path: str = "./data/llm_cache.sqlite"
    langfuse_enabled: bool = False
    langfuse_base_url: str | None = None
    langfuse_release: str = "local"
    langfuse_environment: str = "local"
    cors_origins: list[str] = []
    public_beta_enabled: bool = False
    public_beta_invite_codes: list[str] = []
    public_beta_daily_preflight_limit: int = 20
    public_beta_daily_run_limit: int = 3
    public_beta_require_preflight: bool = True


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_csv(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    """Load settings from environment with safe mock defaults."""
    return Settings(
        mock_mode=_env_bool("MOCK_MODE", True),
        sqlite_path=os.getenv("SQLITE_PATH", "./data/opportunity_miner.db"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./github_opportunity_miner.db"),
        github_graphql_url=os.getenv("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql"),
        llm_api_key=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1",
        llm_model=os.getenv("LLM_MODEL") or os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        github_token=os.getenv("GITHUB_TOKEN"),
        default_model=os.getenv("DEFAULT_MODEL", "mock-llm"),
        validation_mode=os.getenv("VALIDATION_MODE", "strict").strip().lower() or "strict",
        max_llm_concurrency=max(1, _env_int("MAX_LLM_CONCURRENCY", 4)),
        max_github_concurrency=max(1, _env_int("MAX_GITHUB_CONCURRENCY", 3)),
        llm_cache_enabled=_env_bool("LLM_CACHE_ENABLED", True),
        llm_cache_path=os.getenv("LLM_CACHE_PATH", "./data/llm_cache.sqlite"),
        langfuse_enabled=_env_bool("LANGFUSE_ENABLED", False),
        langfuse_base_url=os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST"),
        langfuse_release=os.getenv("LANGFUSE_RELEASE", "local"),
        langfuse_environment=os.getenv("LANGFUSE_ENVIRONMENT", os.getenv("APP_ENV", "local")),
        cors_origins=_env_csv("CORS_ORIGINS"),
        public_beta_enabled=_env_bool("PUBLIC_BETA_ENABLED", False),
        public_beta_invite_codes=_env_csv("PUBLIC_BETA_INVITE_CODES"),
        public_beta_daily_preflight_limit=max(1, _env_int("PUBLIC_BETA_DAILY_PREFLIGHT_LIMIT", 20)),
        public_beta_daily_run_limit=max(1, _env_int("PUBLIC_BETA_DAILY_RUN_LIMIT", 3)),
        public_beta_require_preflight=_env_bool("PUBLIC_BETA_REQUIRE_PREFLIGHT", True),
    )
