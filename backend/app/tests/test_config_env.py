"""Settings environment parsing tests."""

from app.config import get_settings


def test_empty_public_beta_limits_fall_back_to_defaults(monkeypatch):
    monkeypatch.setenv("PUBLIC_BETA_DAILY_PREFLIGHT_LIMIT", "")
    monkeypatch.setenv("PUBLIC_BETA_DAILY_RUN_LIMIT", "")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.public_beta_daily_preflight_limit == 20
    assert settings.public_beta_daily_run_limit == 3
    get_settings.cache_clear()


def test_invalid_integer_settings_fall_back_to_defaults(monkeypatch):
    monkeypatch.setenv("MAX_LLM_CONCURRENCY", "not-a-number")
    monkeypatch.setenv("PUBLIC_BETA_DAILY_RUN_LIMIT", "also-not-a-number")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.max_llm_concurrency == 4
    assert settings.public_beta_daily_run_limit == 3
    get_settings.cache_clear()
