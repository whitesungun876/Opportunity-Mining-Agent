"""Cleaner node unit tests."""

import pytest
from src.nodes.cleaner import (
    clean,
    cleaner_node,
    normalize_text,
    hard_filter,
    spam_score,
    canonicalize,
    DEFAULT_SYNONYMS,
    DEFAULT_SPAM_PATTERNS,
)


def test_cleaner_dedup():
    state = {
        "raw_items": [
            {"content": "  same  "},
            {"content": "SAME"},
            {"snippet": "other"},
        ],
    }
    out = clean(state)
    assert "clean_comments" in out
    assert "cleaned_texts" in out
    assert out["cleaned_texts"] == out["clean_comments"]
    assert len(out["clean_comments"]) <= 2
    assert "dropped_comments" in out
    assert "dedup_groups" in out
    assert "clean_stats" in out
    assert "n_in" in out["clean_stats"]
    assert "n_after_dedup" in out["clean_stats"]


def test_cleaner_empty():
    out = clean({"raw_items": []})
    assert out["clean_comments"] == []
    assert out["cleaned_texts"] == []
    assert out["dropped_comments"] == []
    assert out["dedup_groups"] == []


def test_normalization():
    assert normalize_text("  hello  world  ") == "hello world"
    assert "<URL>" in normalize_text("https://x.com/abc")
    assert normalize_text("@张三") == "<USER>"
    assert "<TAG:" in normalize_text("#话题#") or "<TAG>" in normalize_text("#话题#")


def test_hard_filter_drops_spam():
    # hard_filter returns None (keep) or reason (drop). Short text is low_info first.
    assert hard_filter("正常评论内容足够长", min_len=8, spam_patterns=DEFAULT_SPAM_PATTERNS) is None
    # Long enough text with spam pattern -> spam_promotion
    assert hard_filter("快来私信我加V领取福利", min_len=8, spam_patterns=DEFAULT_SPAM_PATTERNS) == "spam_promotion"
    assert hard_filter("哈哈哈", min_len=8, spam_patterns=DEFAULT_SPAM_PATTERNS) == "low_info_or_too_short"


def test_cleaner_node_drops_spam_and_low_info():
    state = {"raw_comments": ["正常评论内容足够长", "快来私信我加V领取福利", "哈哈哈"]}
    out = cleaner_node(state, min_len=8)
    assert len(out["clean_comments"]) == 1
    assert out["clean_comments"][0] == normalize_text("正常评论内容足够长")
    reasons = [d["reason"] for d in out["dropped_comments"]]
    assert "spam_promotion" in reasons
    assert "low_info_or_too_short" in reasons


def test_near_duplicate_dedup_via_clean():
    state = {"raw_comments": ["价格太贵", "价格 太 贵", "价格太贵"]}
    out = cleaner_node(state, min_len=2)
    assert out["clean_stats"]["n_after_dedup"] <= 2
    assert out["clean_stats"]["n_after_dedup"] >= 1
def test_spam_score():
    score_high, _ = spam_score("私信我加V", DEFAULT_SPAM_PATTERNS)
    assert score_high >= 0.35
    score_low, _ = spam_score("这个产品不错", DEFAULT_SPAM_PATTERNS)
    assert score_low < 0.5


def test_canonicalize():
    assert "价格高" in canonicalize("太贵了", DEFAULT_SYNONYMS)
    assert "订阅付费" in canonicalize("会员费", DEFAULT_SYNONYMS)


def test_clean_from_raw_items():
    """clean() builds raw_comments from raw_items when raw_comments is missing."""
    state = {"raw_items": [{"content": "  a  "}, {"snippet": "b"}]}
    out = clean(state)
    assert "raw_comments" in out
    assert out["raw_comments"] == ["a", "b"]
    # "a"/"b" are dropped by hard_filter (min_len=8), so clean_comments may be empty
    assert "clean_comments" in out
