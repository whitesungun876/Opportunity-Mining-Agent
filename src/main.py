"""Entry point: instantiate graph and run the pipeline."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.graph import build_graph
from src.eval.benchmark import SAMPLE_RAW_ITEMS
from src.eval.metrics import compute_run_report
from src.utils.logger import configure_logging, get_logger
from src.utils.observability import get_node_run_records

load_dotenv()
configure_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

OUTPUT_DIR = Path("./data/runs").resolve()


def _to_serializable(obj: object) -> object:
    """Convert state values for JSON (Pydantic models -> dict)."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_to_serializable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    return obj


def save_run_results(accumulated: dict, run_report: dict) -> None:
    """Write extracted results and report to data/runs/."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    topic_slug = (accumulated.get("topic") or "run")[:30].replace(" ", "_")

    # Full results JSON (extracted pains, clusters, scores, etc.)
    out = {
        "topic": accumulated.get("topic"),
        "extracted_pains": accumulated.get("extracted_pains") or accumulated.get("pain_points"),
        "opportunity_clusters": accumulated.get("opportunity_clusters") or accumulated.get("opportunities"),
        "score_cards": accumulated.get("score_cards"),
        "final_report": accumulated.get("final_report") or accumulated.get("report"),
        "run_report": run_report,
    }
    json_path = OUTPUT_DIR / f"{ts}_{topic_slug}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(_to_serializable(out), f, ensure_ascii=False, indent=2)
    logger.info("Results JSON: %s", json_path)

    # Markdown report (same as final_report)
    md_content = accumulated.get("final_report") or accumulated.get("report") or ""
    if md_content:
        md_path = OUTPUT_DIR / f"{ts}_{topic_slug}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        logger.info("Report MD: %s", md_path)


def main() -> None:
    graph = build_graph()
    initial: dict = {
        "topic": os.getenv("ORACLE_TOPIC", "SaaS startup pain points and opportunities"),
    }
    # Default: use fixture (no browser). Set ORACLE_USE_BROWSER=1 for real browser collect.
    use_browser = os.getenv("ORACLE_USE_BROWSER", "").strip() == "1"
    if not use_browser:
        initial["raw_items"] = SAMPLE_RAW_ITEMS
        logger.info("Using fixture raw_items (set ORACLE_USE_BROWSER=1 for real browser collect)")
    else:
        logger.info("Real browser collect (ORACLE_USE_BROWSER=1)")
    logger.info("Starting oracle run: topic=%s", initial["topic"])
    accumulated: dict = {}
    _node_names = {"collect", "clean", "extract", "cluster", "cards", "validate", "score", "memory", "report"}
    for event in graph.stream(initial):
        logger.debug("Event: %s", list(event.keys()) if isinstance(event, dict) else event)
        if not isinstance(event, dict):
            continue
        # LangGraph may yield {node_name: state_update}; merge the update into accumulated
        if len(event) == 1:
            key, val = next(iter(event.items()))
            if key in _node_names and isinstance(val, dict):
                accumulated = {**accumulated, **val}
                continue
        accumulated = {**accumulated, **event}
    node_timings = get_node_run_records()
    report = compute_run_report(accumulated, node_timings=node_timings)
    logger.info("Run report: %s", json.dumps(report, ensure_ascii=False, default=str))
    save_run_results(accumulated, report)
    logger.info("Run finished.")


if __name__ == "__main__":
    main()
