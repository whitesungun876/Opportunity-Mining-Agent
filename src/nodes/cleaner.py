# src/nodes/cleaner.py
from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple


# ----------------------------
# Config
# ----------------------------

DEFAULT_SYNONYMS = {
    # Price / payment
    "太贵": "价格高",
    "死贵": "价格高",
    "贵死": "价格高",
    "价格劝退": "价格高",
    "割韭菜": "价格高",
    "年费": "订阅付费",
    "月费": "订阅付费",
    "会员": "订阅付费",
    "订阅": "订阅付费",
    "续费": "订阅付费",
    "付费": "订阅付费",
    "按量付费": "按量付费",
    "按次付费": "按量付费",
    "一次性": "一次性买断",
    "买断": "一次性买断",

    # Features / experience
    "基础版": "免费版限制",
    "免费版": "免费版限制",
    "啥也不能用": "免费版限制",
    "不能用": "不可用",
    "卡": "性能问题",
    "很卡": "性能问题",
    "闪退": "稳定性问题",
    "崩溃": "稳定性问题",
    "广告": "广告干扰",
    "太多广告": "广告干扰",
    "引导付费": "订阅付费",
}

# Common promotion/spam patterns (extend as needed)
DEFAULT_SPAM_PATTERNS = [
    r"加[vV微VXx]\s*[:：]?\s*\w+",
    r"私信|私我|dm我|滴滴|进群|拉群",
    r"免费领取|限时福利|点链接|戳这里|评论区见",
    r"带你赚钱|日入|躺赚|暴富|项目",
    r"代理|分销|返佣|推广",
]

# Low-info / junk short comments (extend as needed)
DEFAULT_LOW_INFO = [
    "哈哈", "哈哈哈", "笑死", "yyds", "绝了", "+1", "同感", "支持", "顶", "路过"
]


# ----------------------------
# Data structures
# ----------------------------

@dataclass
class DropItem:
    text: str
    reason: str


@dataclass
class KeepItem:
    original: str
    normalized: str
    canon: str
    spam_score: float
    spam_reasons: List[str]


@dataclass
class DedupGroup:
    kept_index: int
    dropped_indices: List[int]
    reason: str  # exact / normalized / simhash


@dataclass
class CleanStats:
    n_in: int
    n_after_normalize: int
    n_dropped_hard: int
    n_after_hard: int
    n_after_dedup: int
    n_dedup_exact: int
    n_dedup_normalized: int
    n_dedup_simhash: int
    spam_rate: float


# ----------------------------
# Normalization helpers
# ----------------------------

_RE_URL = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
_RE_USER = re.compile(r"@[\w\-\u4e00-\u9fff]+")
_RE_TAG = re.compile(r"#([^#]+)#")
_RE_MULTI_SPACE = re.compile(r"\s+")
_RE_PUNCT = re.compile(r"[，。！？、,.!?]+")

# Rough emoji detection (pragmatic; not exhaustive)
_RE_EMOJI = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]+",
    flags=re.UNICODE,
)

# Only punctuation/symbols
_RE_ONLY_SYMBOLS = re.compile(r"^[\W_]+$", flags=re.UNICODE)


def normalize_text(text: str) -> str:
    if not text:
        return ""
    t = text.strip()

    # Unify URL / @ / hashtag
    t = _RE_URL.sub("<URL>", t)
    t = _RE_USER.sub("<USER>", t)
    t = _RE_TAG.sub(r"<TAG:\1>", t)

    # Unify emoji (optional: can keep emoji as sentiment signal)
    t = _RE_EMOJI.sub("<EMOJI>", t)

    # Collapse whitespace
    t = _RE_MULTI_SPACE.sub(" ", t)

    # Unify consecutive punctuation
    t = _RE_PUNCT.sub("。", t)

    return t.strip()


def normalize_for_hash(text: str) -> str:
    """
    More aggressive normalization for dedup hash:
    - Remove spaces
    - Strip common punctuation
    - Lowercase (for English)
    """
    t = text.lower()
    t = re.sub(r"\s+", "", t)
    # Remove common punctuation (build class via escape to avoid invalid escape warning)
    punct_chars = " \"\"''`·~!@#$%^&*()_=+[]{}|;:，。！？、,.?/<>-"
    t = re.sub("[" + re.escape(punct_chars) + "]", "", t)
    return t


# ----------------------------
# Hard filter
# ----------------------------

def is_low_info(text_norm: str, min_len: int) -> bool:
    if not text_norm:
        return True
    if len(text_norm) < min_len:
        # Too short and no clear info (e.g. only emoji/phrases)
        return True
    # Pure symbols
    if _RE_ONLY_SYMBOLS.match(text_norm):
        return True
    # Common low-info short comments
    for w in DEFAULT_LOW_INFO:
        if text_norm == w or text_norm.startswith(w) and len(text_norm) <= len(w) + 1:
            return True
    return False


def hard_filter(text_norm: str, min_len: int, spam_patterns: List[str]) -> Optional[str]:
    """
    Return None if pass; return reason string if drop.
    """
    if is_low_info(text_norm, min_len=min_len):
        return "low_info_or_too_short"

    # Obvious promotion: drop (or could only apply spam_score)
    for pat in spam_patterns:
        if re.search(pat, text_norm, flags=re.IGNORECASE):
            return "spam_promotion"

    return None


# ----------------------------
# Spam scoring (soft)
# ----------------------------

def spam_score(text_norm: str, extra_patterns: List[str]) -> Tuple[float, List[str]]:
    """
    0~1: higher = more spam-like.
    """
    score = 0.0
    reasons = []

    # Hit promotion patterns: strong signal
    for pat in extra_patterns:
        if re.search(pat, text_norm, flags=re.IGNORECASE):
            score += 0.35
            reasons.append(f"hit:{pat}")

    # Too many <URL> / contact info
    if text_norm.count("<URL>") >= 1:
        score += 0.15
        reasons.append("has_url")

    # Repeated exclamation/exaggeration (weak signal)
    if "。" in text_norm and text_norm.count("。") >= 3:
        score += 0.05
        reasons.append("many_punct")

    # "Free/gift/claim/tutorial/course" etc. (tune per domain)
    if re.search(r"免费|福利|领取|教程|课程|训练营|链接", text_norm):
        score += 0.10
        reasons.append("promo_keywords")

    return min(score, 1.0), reasons


# ----------------------------
# Synonym canonicalization
# ----------------------------

def canonicalize(text_norm: str, synonyms: Dict[str, str]) -> str:
    """
    Produce canon text for clustering:
    light normalization without breaking semantics;
    keep original for evidence.
    """
    t = text_norm
    # Simple replace (can extend to tokenizer)
    for k, v in synonyms.items():
        if k in t:
            t = t.replace(k, v)
    return t


# ----------------------------
# SimHash dedup (near duplicate)
# ----------------------------

def _tokenize_for_simhash(text: str) -> List[str]:
    """
    Loose tokenization for Chinese/English mix:
    - Extract Chinese character runs
    - Extract English/numeric tokens
    """
    if not text:
        return []
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9]{2,}", text.lower())
    return tokens


def simhash64(text: str) -> int:
    """
    64-bit SimHash
    """
    tokens = _tokenize_for_simhash(text)
    if not tokens:
        return 0

    v = [0] * 64
    for tok in tokens:
        # Stable hash -> 64-bit
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16) & ((1 << 64) - 1)
        for i in range(64):
            bit = (h >> i) & 1
            v[i] += 1 if bit == 1 else -1

    out = 0
    for i in range(64):
        if v[i] > 0:
            out |= (1 << i)
    return out


def hamming_distance64(a: int, b: int) -> int:
    return (a ^ b).bit_count()


# ----------------------------
# Main cleaner
# ----------------------------

def cleaner_node(
    state: Dict[str, Any],
    *,
    input_field: str = "raw_comments",
    min_len: int = 8,
    synonyms: Optional[Dict[str, str]] = None,
    spam_patterns: Optional[List[str]] = None,
    enable_simhash: bool = True,
    simhash_threshold: int = 6,
    keep_spam_but_score: bool = True,
) -> Dict[str, Any]:
    """
    Input: state[input_field] -> List[str]
    Output (written to state):
      - clean_items: List[KeepItem as dict]
      - clean_comments: List[str]         (normalized, for extractor)
      - canon_comments: List[str]         (canon, for clusterer)
      - dropped_comments: List[DropItem as dict]
      - dedup_groups: List[DedupGroup as dict]
      - clean_stats: CleanStats as dict
    """
    raw: List[str] = state.get(input_field, []) or []
    synonyms = synonyms or DEFAULT_SYNONYMS
    spam_patterns = spam_patterns or DEFAULT_SPAM_PATTERNS

    # 1) Normalize
    normalized_all = [normalize_text(x) for x in raw]

    dropped: List[DropItem] = []
    kept_stage: List[Tuple[int, str]] = []  # (idx, normalized)

    # 2) Hard filter
    for idx, tnorm in enumerate(normalized_all):
        reason = hard_filter(tnorm, min_len=min_len, spam_patterns=spam_patterns)
        if reason is not None:
            dropped.append(DropItem(text=raw[idx], reason=reason))
        else:
            kept_stage.append((idx, tnorm))

    # 3) Dedup: exact + normalized-hash + simhash
    dedup_groups: List[DedupGroup] = []
    keep_indices: List[int] = []
    seen_exact: Dict[str, int] = {}
    seen_normhash: Dict[str, int] = {}
    simhash_buckets: List[Tuple[int, int]] = []  # (kept_idx_in_kept_stage, simhash)

    n_dedup_exact = 0
    n_dedup_norm = 0
    n_dedup_sim = 0

    for kept_pos, (orig_idx, tnorm) in enumerate(kept_stage):
        # Exact match on normalized text
        if tnorm in seen_exact:
            n_dedup_exact += 1
            dedup_groups.append(DedupGroup(
                kept_index=seen_exact[tnorm],
                dropped_indices=[orig_idx],
                reason="exact",
            ))
            continue
        seen_exact[tnorm] = orig_idx

        # Normalized hash
        h = normalize_for_hash(tnorm)
        if h in seen_normhash:
            n_dedup_norm += 1
            dedup_groups.append(DedupGroup(
                kept_index=seen_normhash[h],
                dropped_indices=[orig_idx],
                reason="normalized",
            ))
            continue
        seen_normhash[h] = orig_idx

        # SimHash near-dup (use aggressively normalized text for stability)
        if enable_simhash:
            sh = simhash64(h)
            is_dup = False
            for prev_kept_pos, prev_sh in simhash_buckets:
                if hamming_distance64(sh, prev_sh) <= simhash_threshold:
                    # Near-dup: drop current
                    n_dedup_sim += 1
                    kept_orig_idx = kept_stage[prev_kept_pos][0]
                    dedup_groups.append(DedupGroup(
                        kept_index=kept_orig_idx,
                        dropped_indices=[orig_idx],
                        reason="simhash",
                    ))
                    is_dup = True
                    break
            if is_dup:
                continue
            simhash_buckets.append((kept_pos, sh))

        keep_indices.append(orig_idx)

    # 4) Spam scoring + 5) Canonicalization
    clean_items: List[KeepItem] = []
    spam_count = 0

    for orig_idx in keep_indices:
        original = raw[orig_idx]
        tnorm = normalized_all[orig_idx]

        s_score, s_reasons = spam_score(tnorm, extra_patterns=spam_patterns)
        if s_score >= 0.6:
            spam_count += 1
            if not keep_spam_but_score:
                dropped.append(DropItem(text=original, reason="spam_scored_drop"))
                continue

        canon = canonicalize(tnorm, synonyms=synonyms)

        clean_items.append(
            KeepItem(
                original=original,
                normalized=tnorm,
                canon=canon,
                spam_score=s_score,
                spam_reasons=s_reasons,
            )
        )

    clean_comments = [x.normalized for x in clean_items]
    canon_comments = [x.canon for x in clean_items]

    stats = CleanStats(
        n_in=len(raw),
        n_after_normalize=len(normalized_all),
        n_dropped_hard=len([d for d in dropped if d.reason in ("low_info_or_too_short", "spam_promotion")]),
        n_after_hard=len(kept_stage),
        n_after_dedup=len(clean_items),
        n_dedup_exact=n_dedup_exact,
        n_dedup_normalized=n_dedup_norm,
        n_dedup_simhash=n_dedup_sim,
        spam_rate=(spam_count / len(clean_items)) if clean_items else 0.0,
    )

    return {
        "clean_items": [asdict(x) for x in clean_items],
        "clean_comments": clean_comments,
        "cleaned_texts": clean_comments,
        "canon_comments": canon_comments,
        "dropped_comments": [asdict(x) for x in dropped],
        "dedup_groups": [asdict(x) for x in dedup_groups],
        "clean_stats": asdict(stats),
    }


def _texts_from_state(state: Dict[str, Any]) -> List[str]:
    """Build raw comment list from state: raw_comments or raw_items (content/snippet/body)."""
    raw_comments = state.get("raw_comments")
    if raw_comments is not None:
        return [c if isinstance(c, str) else str(c) for c in raw_comments]
    raw_items = state.get("raw_items") or []
    texts: List[str] = []
    for item in raw_items:
        if isinstance(item, dict):
            t = item.get("content") or item.get("snippet") or item.get("body") or ""
        else:
            t = str(item)
        if t:
            texts.append(t.strip())
    return texts


def clean(
    state: Dict[str, Any],
    *,
    input_field: str = "raw_comments",
    min_len: int = 8,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Entry point for the graph: ensures raw_comments from raw_items if needed,
    runs cleaner_node, and merges result back into state.
    """
    raw_texts = _texts_from_state(state)
    state_with_input = {**state, "raw_comments": raw_texts}
    result = cleaner_node(state_with_input, input_field=input_field, min_len=min_len, **kwargs)
    return {**state, "raw_comments": raw_texts, **result}
