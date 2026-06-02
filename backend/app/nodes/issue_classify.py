"""Issue classifier node with mock rules and optional real LLM mode."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.context.builders import build_context_packet
from app.graph.state import GraphState
from app.harness.llm_runner import LLMRunner
from app.harness.trace_logger import JsonTraceLogger
from app.services.llm_client import LLMClient, parse_json_object


LOW_VALUE_RULES = [
    ("one-off bug", ["one-off bug"]),
    ("local environment issue", ["local", "my laptop", "environment"]),
    ("vague \"it doesn't work\"", ["it doesn't work", "doesnt work"]),
    ("simple install error", ["install fails", "pip install", "npm install"]),
    ("duplicate support request", ["duplicate", "how to set env"]),
]

HIGH_VALUE_RULES = [
    ("architecture discussion", ["architecture discussion", "architecture"]),
    ("integration challenge", ["integrating", "integration challenge", "existing ci"]),
    ("performance issue at scale", ["performance", "scale", "latency spikes"]),
    ("production deployment blocker", ["production", "deployment", "blocking production"]),
    ("missing production workflow feature", ["missing workflow", "workflow feature", "regression datasets"]),
    ("enterprise/security/permission need", ["enterprise", "security", "permission"]),
    ("observability/evaluation/debugging gap", ["observability", "evaluation", "debugging", "trace"]),
]

ISSUE_CLASSIFIER_SCHEMA = {
    "evidence_id": "str",
    "value_level": "high_value | low_value",
    "category": "str",
    "reason": "str",
    "labels_matched": "list[str]",
    "should_extract_pain": "bool",
}


def _load_prompt() -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / "issue_classifier.txt"
    return path.read_text(encoding="utf-8")


def _evidence_id(issue: dict) -> str:
    return str(issue.get("evidence_id") or issue.get("issue_id") or issue.get("id") or issue.get("url") or "")


def _comment_texts(issue: dict, max_comments: int = 3, max_chars: int = 700) -> list[str]:
    comments = issue.get("comments") or []
    out: list[str] = []
    if isinstance(comments, list):
        for comment in comments[:max_comments]:
            if isinstance(comment, dict):
                text = comment.get("body") or comment.get("bodyText") or ""
            else:
                text = str(comment)
            text = text.strip()
            if text:
                out.append(text[:max_chars])
    return out


def _issue_context(issue: dict) -> dict:
    return {
        "evidence_id": _evidence_id(issue),
        "source_url": issue.get("source_url") or issue.get("url"),
        "title": issue.get("title", "")[:400],
        "body": (issue.get("body") or issue.get("bodyText") or "")[:2400],
        "labels": issue.get("labels") or [],
        "comments": _comment_texts(issue),
        "comment_count": issue.get("comment_count", issue.get("comments_count", 0)),
    }


def parse_issue_classifier_response(response: str | dict[str, Any], issue: dict) -> dict:
    """Validate and normalize a real LLM classifier response."""
    data = parse_json_object(response)
    evidence_id = str(data.get("evidence_id") or _evidence_id(issue))
    value_level = str(data.get("value_level") or data.get("value_class") or "").strip()
    if value_level not in {"high_value", "low_value"}:
        value_level = "low_value"
    labels_matched = data.get("labels_matched") or []
    if not isinstance(labels_matched, list):
        labels_matched = [str(labels_matched)]
    should_extract = bool(data.get("should_extract_pain", value_level == "high_value"))
    if value_level == "low_value":
        should_extract = False
    category = str(data.get("category") or ("production signal" if value_level == "high_value" else "low_value")).strip()
    reason = str(data.get("reason") or category).strip()
    return {
        **issue,
        "evidence_id": evidence_id,
        "value_level": value_level,
        "value_class": value_level,
        "category": category,
        "reason": reason,
        "labels_matched": [str(label) for label in labels_matched if str(label).strip()],
        "should_extract_pain": should_extract,
    }


def classify_issue(issue: dict) -> dict:
    """Classify one GitHub issue using deterministic MVP rules."""
    text = f"{issue.get('title', '')} {issue.get('body', '')} {' '.join(issue.get('labels', []))}".lower()
    for reason, needles in LOW_VALUE_RULES:
        if any(needle in text for needle in needles):
            return {
                **issue,
                "evidence_id": _evidence_id(issue),
                "value_level": "low_value",
                "value_class": "low_value",
                "category": reason,
                "reason": reason,
                "labels_matched": [],
                "should_extract_pain": False,
            }
    for reason, needles in HIGH_VALUE_RULES:
        matched = [needle for needle in needles if needle in text]
        if matched:
            return {
                **issue,
                "evidence_id": _evidence_id(issue),
                "value_level": "high_value",
                "value_class": "high_value",
                "category": reason,
                "reason": reason,
                "labels_matched": matched,
                "should_extract_pain": True,
            }
    if issue.get("comments_count", 0) >= 5 and "production" in text:
        return {
            **issue,
            "evidence_id": _evidence_id(issue),
            "value_level": "high_value",
            "value_class": "high_value",
            "category": "production deployment blocker",
            "reason": "production deployment blocker",
            "labels_matched": ["production"],
            "should_extract_pain": True,
        }
    return {
        **issue,
        "evidence_id": _evidence_id(issue),
        "value_level": "low_value",
        "value_class": "low_value",
        "category": "vague \"it doesn't work\"",
        "reason": "vague \"it doesn't work\"",
        "labels_matched": [],
        "should_extract_pain": False,
    }


def _trace_llm_call(
    state: GraphState,
    *,
    evidence_id: str,
    output_data: dict,
    latency_ms: float,
    errors: list[str],
    model: str,
) -> None:
    logger = state.get("_trace_logger")
    if not isinstance(logger, JsonTraceLogger):
        return
    logger.log(
        run_id=state.get("run_id", "local"),
        node_name="issue_classify.llm",
        input_data={"evidence_id": evidence_id},
        output_data={"evidence_id": evidence_id, **output_data},
        latency_ms=latency_ms,
        errors=errors,
        prompt_version="issue_classifier:real-v1",
        model=model,
        is_mock=False,
    )


def _classify_issue_with_llm(state: GraphState, issue: dict, client: LLMClient) -> tuple[dict | None, str | None]:
    evidence_id = _evidence_id(issue)
    packet = build_context_packet(
        node_name="issue_classify",
        goal="Classify one GitHub issue as high-value production pain or low-value noise.",
        input_items=[_issue_context(issue)],
        evidence_ids=[evidence_id],
        output_schema=ISSUE_CLASSIFIER_SCHEMA,
        prompt_version="issue_classifier:real-v1",
    )
    prompt = (
        _load_prompt()
        + "\n\nContextPacket:\n"
        + packet.model_dump_json(indent=2)
    )
    start = time.perf_counter()
    try:
        response = client.structured(prompt, ISSUE_CLASSIFIER_SCHEMA, system_prompt="You are a strict JSON classifier.")
        parsed = parse_issue_classifier_response(response, issue)
        _trace_llm_call(
            state,
            evidence_id=evidence_id,
            output_data=parsed,
            latency_ms=(time.perf_counter() - start) * 1000,
            errors=[],
            model=client.model,
        )
        return parsed, None
    except Exception as exc:
        error = f"issue_classify {evidence_id}: {type(exc).__name__}: {exc}"
        _trace_llm_call(
            state,
            evidence_id=evidence_id,
            output_data={},
            latency_ms=(time.perf_counter() - start) * 1000,
            errors=[error],
            model=client.model,
        )
        return None, error


def issue_classify(state: GraphState) -> GraphState:
    settings = get_settings()
    issues = state.get("ranked_evidence_items") or state.get("raw_issues") or []
    errors = list(state.get("errors") or [])
    use_real_llm = (not settings.mock_mode) and bool(settings.llm_api_key)

    if use_real_llm:
        runner = LLMRunner(max_concurrency=settings.max_llm_concurrency)
        with LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            mock_mode=False,
            cache_enabled=settings.llm_cache_enabled,
        ) as client:
            results = runner.run_many(
                issues,
                lambda issue: _classify_issue_with_llm(state, issue, client),
            )
        classified = []
        for issue, (parsed, error) in zip(issues, results):
            if parsed is not None:
                classified.append(parsed)
            else:
                errors.append(error or f"issue_classify {_evidence_id(issue)} failed")
                classified.append({**classify_issue(issue), "llm_error": error})
    else:
        classified = [classify_issue(issue) for issue in issues]

    classified = [
        {
            **issue,
            "issue_id": issue.get("issue_id") or issue.get("evidence_id") or _evidence_id(issue),
        }
        for issue in classified
    ]
    high = [issue for issue in classified if issue.get("value_class") == "high_value"]
    low = [issue for issue in classified if issue.get("value_class") == "low_value"]
    quality_score = len(high) / max(1, len(classified))
    return {
        **state,
        "classified_issues": classified,
        "high_value_issues": high,
        "low_value_issues": low,
        "errors": errors,
        "quality_score": round(quality_score, 3),
    }
