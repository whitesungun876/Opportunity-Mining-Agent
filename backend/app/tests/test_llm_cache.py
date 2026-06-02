"""LLM cache tests."""

from app.harness.llm_cache import LLMCache, stable_hash


def test_llm_cache_round_trip(tmp_path):
    cache = LLMCache(tmp_path / "llm_cache.sqlite")
    key = stable_hash({"node": "issue_classify", "evidence_id": "ev1"})
    value = {"value_level": "high_value", "reason": "production workflow blocker"}

    cache.set(key, value)

    assert cache.get(key) == value
    cache.close()


def test_stable_hash_ignores_dict_order():
    assert stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})
