# src/nodes/collector.py
from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


# Tune as needed: default uses "web search + forums/comments" to gather complaints
COLLECTOR_SYSTEM = """
You are a "social media / web comment collector". Your goal: given a topic, find real user complaints, grievances, rants, or negative reviews.

Requirements:
- Collect only verbatim user quotes; do not summarize or paraphrase.
- Each item ≤ 120 characters; keep tone and filler words when possible.
- Filter out marketing copy, pure memes, and off-topic content.
- Use multiple sources (at least 3 different pages/sites); prefer comment sections, forums, Q&A.
- Output must be strict JSON only: {"items": ["comment1", "comment2", ...]}, with no extra text.
"""


def _extract_json_items(text: str) -> List[str]:
    """
    Try to parse {"items": [...]} from the Agent output.
    """
    # 1) Try parsing the whole string as JSON
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and isinstance(obj.get("items"), list):
            return [str(x).strip() for x in obj["items"] if str(x).strip()]
    except Exception:
        pass

    # 2) Extract first {...} JSON block from text
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        blob = m.group(0)
        try:
            obj = json.loads(blob)
            if isinstance(obj, dict) and isinstance(obj.get("items"), list):
                return [str(x).strip() for x in obj["items"] if str(x).strip()]
        except Exception:
            pass

    # 3) Give up: return empty
    return []


async def _run_browseruse_collect(
    topic: str,
    *,
    max_items: int = 50,
    seed_queries: Optional[List[str]] = None,
    extra_instructions: str = "",
    use_cloud_browser: bool = False,
    target_url: Optional[str] = None,
) -> List[str]:
    """
    Run one browser-use collection task; return raw comments as list[str].
    If target_url is set, the Agent is instructed to open that URL first and scrape comments.
    """
    from browser_use import Agent, Browser, ChatBrowserUse

    load_dotenv()

    browser = Browser(use_cloud=use_cloud_browser)
    llm = ChatBrowserUse()

    seed_queries = seed_queries or [
        f"{topic} negative reviews",
        f"{topic} complaints",
        f"{topic} too expensive subscription",
        f"{topic} alternative",
    ]

    if target_url and target_url.strip():
        task = f"""
{COLLECTOR_SYSTEM}

Topic: {topic}
Target URL (open this page first): {target_url.strip()}
Max items: {max_items}

Extra requirements:
{extra_instructions}

Steps:
1) Navigate to the Target URL above.
2) Scroll and load the page to reveal user posts/comments/notes.
3) Extract verbatim user quotes from the page.
4) Output strict JSON only: {{"items": ["comment1", "comment2", ...]}}, items count <= {max_items}.
"""
    else:
        task = f"""
{COLLECTOR_SYSTEM}

Topic: {topic}
Suggested search queries: {seed_queries}
Max items: {max_items}

Extra requirements:
{extra_instructions}

Suggested steps:
1) Search the above keywords in a search engine
2) Open several result pages; find comment sections, Q&A, forum posts
3) Extract verbatim user quotes
4) Output JSON: {{"items": [...]}}, with items count <= {max_items}
"""

    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
    )

    history = await agent.run()

    # history string usually contains the final output; best-effort parse
    text = str(history)
    items = _extract_json_items(text)

    # Dedupe and cap
    seen = set()
    dedup: List[str] = []
    for x in items:
        x = x.strip()
        if not x:
            continue
        if x in seen:
            continue
        seen.add(x)
        dedup.append(x)
        if len(dedup) >= max_items:
            break

    return dedup


def collect(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: read state, return state merged with raw_comments (and raw_items for compat).
    If state already has raw_items, skip browser and use them (for fixture/smoke runs).
    Updates total_items (cumulative) and previous_evidence_count for policy gates.
    """
    # Carry previous_evidence_count and increment iteration (for policy gates)
    iteration_count = (state.get("iteration_count") or 0) + 1
    state = {
        **state,
        "previous_evidence_count": state.get("current_evidence_count") or state.get("previous_evidence_count"),
        "iteration_count": iteration_count,
    }

    topic = (state.get("topic") or "").strip()
    if not topic:
        return {**state, "raw_comments": [], "raw_items": []}

    # Use existing raw_items when provided (e.g. fixture / smoke run)
    existing = state.get("raw_items") or []
    if existing and len(existing) > 0:
        comments = [
            (x.get("content") if isinstance(x, dict) else str(x)).strip()
            for x in existing
            if (x.get("content") if isinstance(x, dict) else str(x)).strip()
        ]
        # Streaming: return batches for process_batch loop (clean+extract per batch)
        streaming = state.get("_streaming_collect") is True or (os.getenv("ORACLE_STREAMING_COLLECT", "").strip() == "1")
        batch_size = int(state.get("_streaming_batch_size") or os.getenv("ORACLE_STREAMING_BATCH_SIZE", "50") or 50)
        if streaming and len(comments) > batch_size:
            batches = [comments[i : i + batch_size] for i in range(0, len(comments), batch_size)]
            return {
                **state,
                "_collect_batches": batches,
                "_collect_index": 0,
                "raw_comments": [],
                "raw_items": [],
                "iteration_count": iteration_count,
            }
        # Fixture path: do not add to total_items (Budget Gate applies to real collection only)
        return {**state, "raw_comments": comments, "raw_items": existing, "iteration_count": iteration_count}

    cfg = state.get("collector", {}) or {}
    max_items = int(cfg.get("max_items", 50))
    seed_queries = cfg.get("seed_queries")
    extra_instructions = str(cfg.get("extra_instructions", ""))
    use_cloud_browser = bool(cfg.get("use_cloud_browser", False))
    # Optional: open a specific URL (any site). target_url directly, or build from search_keyword + url_template.
    target_url = (cfg.get("target_url") or os.getenv("ORACLE_TARGET_URL", "") or "").strip()
    search_keyword = (cfg.get("search_keyword") or os.getenv("ORACLE_SEARCH_KEYWORD", "") or "").strip()
    url_template = (cfg.get("url_template") or os.getenv("ORACLE_COLLECT_URL_TEMPLATE", "") or "").strip()
    if not target_url and search_keyword and url_template and "{search_keyword}" in url_template:
        target_url = url_template.format(search_keyword=search_keyword)

    comments = asyncio.run(
        _run_browseruse_collect(
            topic,
            max_items=max_items,
            seed_queries=seed_queries,
            extra_instructions=extra_instructions,
            use_cloud_browser=use_cloud_browser,
            target_url=target_url or None,
        )
    )
    # raw_items: list[dict] for backward compat with cleaner _texts_from_state
    raw_items = [{"content": c} for c in comments]
    total_items = (state.get("total_items") or 0) + len(comments)
    # Streaming: return batches for process_batch loop
    streaming = state.get("_streaming_collect") is True or (os.getenv("ORACLE_STREAMING_COLLECT", "").strip() == "1")
    batch_size = int(state.get("_streaming_batch_size") or os.getenv("ORACLE_STREAMING_BATCH_SIZE", "50") or 50)
    if streaming and len(comments) > batch_size:
        batches = [comments[i : i + batch_size] for i in range(0, len(comments), batch_size)]
        return {
            **state,
            "_collect_batches": batches,
            "_collect_index": 0,
            "raw_comments": [],
            "raw_items": [],
            "total_items": total_items,
            "iteration_count": iteration_count,
        }
    return {**state, "raw_comments": comments, "raw_items": raw_items, "total_items": total_items, "iteration_count": iteration_count}


def collector_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Alias for LangGraph: same as collect(state).
    """
    return collect(state)
