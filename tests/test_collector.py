"""Collector node tests (unit + mock; no real browser)."""

import pytest
from unittest.mock import patch

from src.nodes.collector import (
    collect,
    _extract_json_items,
    COLLECTOR_SYSTEM,
)


# ---- _extract_json_items ----

def test_extract_json_items_valid_json():
    text = '{"items": ["a", "b", "c"]}'
    assert _extract_json_items(text) == ["a", "b", "c"]


def test_extract_json_items_embedded():
    text = 'Here is the result:\n{"items": ["only one"]}\nDone.'
    assert _extract_json_items(text) == ["only one"]


def test_extract_json_items_empty_items():
    text = '{"items": []}'
    assert _extract_json_items(text) == []


def test_extract_json_items_strips_and_skips_blank():
    text = '{"items": ["  x  ", "", "y"]}'
    assert _extract_json_items(text) == ["x", "y"]


def test_extract_json_items_no_items_key():
    text = '{"other": [1, 2]}'
    assert _extract_json_items(text) == []


def test_extract_json_items_invalid_json():
    assert _extract_json_items("not json at all") == []
    assert _extract_json_items("") == []


# ---- collect (node) ----

def test_collect_empty_topic():
    out = collect({})
    assert out["raw_comments"] == []
    assert out["raw_items"] == []

    out = collect({"query": "  ", "topic": ""})
    assert out["raw_comments"] == []
    assert out["raw_items"] == []


def test_collect_uses_query_when_no_topic():
    async def mock_run(*args, **kwargs):
        return ["from query"]

    with patch("src.nodes.collector._run_browseruse_collect", new=mock_run):
        out = collect({"query": "Perplexity"})
    assert out["raw_comments"] == ["from query"]
    assert out["raw_items"] == [{"content": "from query"}]
    assert out["query"] == "Perplexity"


def test_collect_with_mock_returns_raw_comments_and_raw_items():
    async def mock_run(topic, *, max_items=50, **kwargs):
        return [f"complaint about {topic}", "another one"]

    with patch("src.nodes.collector._run_browseruse_collect", new=mock_run):
        out = collect({"topic": "Netflix", "query": "q"})
    assert out["raw_comments"] == ["complaint about Netflix", "another one"]
    assert out["raw_items"] == [
        {"content": "complaint about Netflix"},
        {"content": "another one"},
    ]
    assert out["topic"] == "Netflix"


def test_collect_respects_collector_config():
    async def mock_run(topic, *, max_items=50, seed_queries=None, **kwargs):
        return [f"max={max_items}", f"queries={seed_queries}"]

    with patch("src.nodes.collector._run_browseruse_collect", new=mock_run):
        out = collect({
            "topic": "X",
            "collector": {
                "max_items": 10,
                "seed_queries": ["custom A", "custom B"],
            },
        })
    assert "max=10" in out["raw_comments"][0]
    assert "custom" in out["raw_comments"][1]


def test_collector_system_mentions_json():
    assert "items" in COLLECTOR_SYSTEM
    assert "JSON" in COLLECTOR_SYSTEM
