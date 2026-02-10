"""Streaming collect: process batches with clean+extract per batch and merge.

When _collect_batches is set, the graph loops over process_batch until all batches
are done; each batch is cleaned and extracted independently, then merged into state.
"""

from __future__ import annotations

from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


def process_batch(state: dict[str, Any]) -> dict[str, Any]:
    """
    Process one batch from _collect_batches[_collect_index]: run clean then extract,
    merge results into accumulated raw_comments, clean_comments, canon_comments, pain_points, extracted_pains.
    """
    batches = state.get("_collect_batches") or []
    idx = state.get("_collect_index") or 0
    if idx >= len(batches):
        return state

    batch_raw: list[str] = batches[idx]
    if not batch_raw:
        return {**state, "_collect_index": idx + 1}

    from src.nodes.cleaner import clean
    from src.nodes.extractor import extract

    # Clean this batch
    batch_state = {**state, "raw_comments": batch_raw}
    clean_out = clean(batch_state)
    clean_comments_batch = clean_out.get("clean_comments") or []
    canon_batch = clean_out.get("canon_comments") or []

    # Extract this batch
    extract_state = {
        **state,
        "clean_comments": clean_comments_batch,
        "cleaned_texts": clean_comments_batch,
        "canon_comments": canon_batch,
    }
    extract_out = extract(extract_state)
    pains_batch = extract_out.get("pain_points") or extract_out.get("extracted_pains") or []

    # Merge into accumulated
    raw_acc = list(state.get("raw_comments") or []) + batch_raw
    clean_acc = list(state.get("clean_comments") or []) + clean_comments_batch
    canon_acc = list(state.get("canon_comments") or []) + canon_batch
    pains_acc = list(state.get("pain_points") or []) + pains_batch
    extracted_acc = list(state.get("extracted_pains") or []) + pains_batch

    logger.info(
        "Streaming process_batch: batch %d/%d, batch_size=%d, accumulated raw=%d pains=%d",
        idx + 1,
        len(batches),
        len(batch_raw),
        len(raw_acc),
        len(pains_acc),
    )

    raw_items_acc = [{"content": c} for c in raw_acc]
    return {
        **state,
        "raw_comments": raw_acc,
        "raw_items": raw_items_acc,
        "clean_comments": clean_acc,
        "canon_comments": canon_acc,
        "cleaned_texts": clean_acc,
        "pain_points": pains_acc,
        "extracted_pains": extracted_acc,
        "clean_stats": clean_out.get("clean_stats"),
        "dropped_comments": (state.get("dropped_comments") or []) + (clean_out.get("dropped_comments") or []),
        "dedup_groups": (state.get("dedup_groups") or []) + (clean_out.get("dedup_groups") or []),
        "_collect_index": idx + 1,
    }
