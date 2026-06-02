"""Pain extraction node."""

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
from app.skills.pain_extract import extract_pains


PAIN_TYPES = {
    "deployment_complexity",
    "configuration_complexity",
    "integration_gap",
    "missing_ui",
    "missing_workflow",
    "performance_at_scale",
    "enterprise_security_gap",
    "permission_gap",
    "observability_gap",
    "evaluation_gap",
    "documentation_gap",
    "maintenance_burden",
    "unclear",
}

PAIN_EXTRACTOR_SCHEMA = {
    "pain_id": "str",
    "evidence_id": "str",
    "pain_type": "str",
    "complaint": "str",
    "persona": "str",
    "context": "str",
    "severity": "float 0..1",
    "workaround": "str",
    "business_signal": "str",
    "supporting_quote": "str",
}


PAIN_EXTRACT_BUDGET_BY_SCOPE = {
    "repo_specific": 12,
    "focused": 16,
    "broad": 20,
    "ambiguous": 0,
}


def _load_prompt() -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / "pain_extractor.txt"
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
        "value_level": issue.get("value_level") or issue.get("value_class"),
        "category": issue.get("category"),
        "reason": issue.get("reason"),
        "title": issue.get("title", "")[:400],
        "body": (issue.get("body") or issue.get("bodyText") or "")[:2600],
        "comments": _comment_texts(issue),
        "labels": issue.get("labels") or [],
    }


def _source_text(issue: dict) -> str:
    parts = [issue.get("title") or "", issue.get("body") or issue.get("bodyText") or ""]
    parts.extend(_comment_texts(issue, max_comments=10, max_chars=1200))
    return "\n".join(part for part in parts if part)


def _coerce_severity(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, score))


def parse_pain_extractor_response(response: str | dict[str, Any], issue: dict) -> dict:
    """Validate and normalize a real LLM pain extractor response."""
    data = parse_json_object(response)
    evidence_id = str(data.get("evidence_id") or _evidence_id(issue))
    pain_type = str(data.get("pain_type") or "unclear").strip()
    if pain_type not in PAIN_TYPES:
        pain_type = "unclear"
    supporting_quote = str(data.get("supporting_quote") or "").strip()
    source_text = _source_text(issue)
    if not supporting_quote or supporting_quote not in source_text:
        supporting_quote = (issue.get("title") or source_text[:240] or "").strip()
    pain_id = str(data.get("pain_id") or f"pain_{evidence_id}")
    return {
        "pain_id": pain_id,
        "issue_id": issue.get("issue_id"),
        "evidence_id": evidence_id,
        "evidence_ids": [evidence_id],
        "pain_type": pain_type,
        "complaint": str(data.get("complaint") or issue.get("title") or "").strip(),
        "persona": str(data.get("persona") or "production engineering team").strip(),
        "context": str(data.get("context") or "using the open-source project in production").strip(),
        "severity": _coerce_severity(data.get("severity")),
        "workaround": str(data.get("workaround") or "").strip(),
        "business_signal": str(data.get("business_signal") or "weak").strip() or "weak",
        "supporting_quote": supporting_quote,
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
        node_name="pain_extract.llm",
        input_data={"evidence_id": evidence_id},
        output_data={"evidence_id": evidence_id, **output_data},
        latency_ms=latency_ms,
        errors=errors,
        prompt_version="pain_extractor:real-v1",
        model=model,
        is_mock=False,
    )


def _extract_pain_with_llm(state: GraphState, issue: dict, client: LLMClient) -> tuple[dict | None, str | None]:
    evidence_id = _evidence_id(issue)
    packet = build_context_packet(
        node_name="pain_extract",
        goal="Extract one structured production pain point from one high-value GitHub issue.",
        input_items=[_issue_context(issue)],
        evidence_ids=[evidence_id],
        output_schema=PAIN_EXTRACTOR_SCHEMA,
        prompt_version="pain_extractor:real-v1",
    )
    prompt = (
        _load_prompt()
        + "\n\nContextPacket:\n"
        + packet.model_dump_json(indent=2)
    )
    start = time.perf_counter()
    try:
        response = client.structured(prompt, PAIN_EXTRACTOR_SCHEMA, system_prompt="You are a strict JSON pain extractor.")
        parsed = parse_pain_extractor_response(response, issue)
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
        error = f"pain_extract {evidence_id}: {type(exc).__name__}: {exc}"
        _trace_llm_call(
            state,
            evidence_id=evidence_id,
            output_data={},
            latency_ms=(time.perf_counter() - start) * 1000,
            errors=[error],
            model=client.model,
        )
        return None, error


def _pain_extract_budget(state: GraphState, total: int) -> int:
    plan = state.get("search_plan") or {}
    scope = str(plan.get("query_scope") or "")
    budget = PAIN_EXTRACT_BUDGET_BY_SCOPE.get(scope, 18)
    return max(0, min(total, budget))


def pain_extract(state: GraphState) -> GraphState:
    settings = get_settings()
    high_value_issues = state.get("high_value_issues") or []
    errors = list(state.get("errors") or [])
    evidence_ids = {item.get("evidence_id") for item in (state.get("evidence_items") or [])}
    use_real_llm = (not settings.mock_mode) and bool(settings.llm_api_key)

    if use_real_llm:
        budget = _pain_extract_budget(state, len(high_value_issues))
        high_value_issues = high_value_issues[:budget]
        runner = LLMRunner(max_concurrency=settings.max_llm_concurrency)
        with LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            mock_mode=False,
            cache_enabled=settings.llm_cache_enabled,
        ) as client:
            results = runner.run_many(
                high_value_issues,
                lambda issue: _extract_pain_with_llm(state, issue, client),
            )
        pains = []
        for issue, (parsed, error) in zip(high_value_issues, results):
            if parsed is None:
                errors.append(error or f"pain_extract {_evidence_id(issue)} failed")
                continue
            if parsed["evidence_id"] not in evidence_ids:
                errors.append(f"pain_extract {parsed['evidence_id']}: evidence_id not found in evidence_items")
                continue
            pains.append(parsed)
    else:
        packet = build_context_packet(
            node_name="pain_extract",
            goal="Extract production pain points from high-value GitHub issues.",
            input_items=high_value_issues,
            evidence_ids=[_evidence_id(issue) for issue in high_value_issues],
            output_schema={"pain_points": "list[dict]"},
            prompt_version="pain_extractor:mock-v1",
        )
        pains = extract_pains(packet.input_items)

    return {**state, "pain_points": pains, "pain_extract_budget": len(high_value_issues), "errors": errors}
