"""Reproducible live quality test for real GitHub + real LLM mode.

The runner injects a YAML benchmark profile into the main LangGraph workflow so
quality tests are comparable across versions without becoming the product
search path. It can also attach Langfuse traces and scores for dashboard review.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.eval.live_smoke import validation_diagnostics
from app.eval.topic_profiles import list_profile_summaries, resolve_profile
from app.graph.main_graph import run_graph
from app.harness.langfuse_observer import LangfuseObserver


AUDIT_ARTIFACT_KEYS = [
    "opportunity_cards",
    "validated_cards",
    "rejected_cards",
    "agent_reviews",
    "final_decisions",
    "evidence_items",
    "opportunity_graph",
    "repo_capabilities",
    "research_evidence",
    "fusion_candidates",
    "validated_fusion_candidates",
    "rejected_fusion_candidates",
    "errors",
]


def _json_default(value: Any) -> str:
    return str(value)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")


def _str_to_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def quality_summary(
    state: dict[str, Any],
    *,
    topic: str,
    profile_id: str,
    artifact_dir: Path,
    started_at: str,
    mode: str = "profile",
) -> dict[str, Any]:
    return {
        "run_id": state.get("run_id"),
        "topic": topic,
        "profile_id": profile_id,
        "mode": mode,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "artifact_dir": str(artifact_dir),
        "raw_issues": len(state.get("raw_issues") or []),
        "evidence_items": len(state.get("evidence_items") or []),
        "classified_issues": len(state.get("classified_issues") or []),
        "high_value_issues": len(state.get("high_value_issues") or []),
        "low_value_issues": len(state.get("low_value_issues") or []),
        "pain_points": len(state.get("pain_points") or []),
        "pain_clusters": len(state.get("pain_clusters") or []),
        "commercial_gaps": len(state.get("commercial_gaps") or []),
        "opportunity_cards": len(state.get("opportunity_cards") or []),
        "validated_cards": len(state.get("validated_cards") or []),
        "rejected_cards": len(state.get("rejected_cards") or []),
        "agent_reviews": len(state.get("agent_reviews") or []),
        "final_decisions": len(state.get("final_decisions") or []),
        "report_len": len(state.get("report_markdown") or ""),
        "report_has_github": "github.com" in (state.get("report_markdown") or ""),
        "errors": len(state.get("errors") or []),
        "langfuse_trace_url": state.get("langfuse_trace_url"),
    }


def run_live_quality(
    *,
    topic: str,
    per_query: int | None,
    max_issues: int | None,
    output_dir: Path,
    profile_id: str | None = None,
    profiles_file: str | None = None,
    skip_debate: bool = False,
    dynamic_search: bool = False,
) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    settings = get_settings()
    observer = LangfuseObserver(settings)
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = str(uuid4())
    artifact_dir = output_dir / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    profile = None if dynamic_search else resolve_profile(topic=topic, profile_id=profile_id, path=profiles_file)
    profile_label = "dynamic_search" if dynamic_search else (profile.profile_id if profile else "generic")
    queries = [] if dynamic_search else profile.render_queries(topic)  # type: ignore[union-attr]
    per_query = per_query or (profile.default_per_query if profile else None)
    max_issues = max_issues or (profile.default_max_issues if profile else None)

    initial_state: dict[str, Any] = {
        "run_id": run_id,
        "user_query": topic,
        "canonical_topic": topic,
        "skip_debate": skip_debate,
        "errors": [],
    }
    if dynamic_search:
        initial_state["iteration_count"] = 0
    else:
        initial_state.update(
            {
                "benchmark_profile_id": profile.profile_id,  # type: ignore[union-attr]
                "benchmark_profile": profile.model_dump(),  # type: ignore[union-attr]
                "benchmark_queries": queries,
                "benchmark_quality_keywords": profile.quality_keywords,  # type: ignore[union-attr]
                "benchmark_per_query": per_query,
                "benchmark_max_issues": max_issues,
                # Keep live quality on one benchmark pass instead of expanding queries,
                # so profile-to-profile comparisons stay stable.
                "iteration_count": 2,
            }
        )

    print("QUALITY_TEST_START", started_at, flush=True)
    print(
        "SETUP",
        "mode",
        "dynamic" if dynamic_search else "profile",
        "profile",
        profile_label,
        "queries",
        len(queries),
        "per_query",
        per_query,
        "max_issues",
        max_issues,
        flush=True,
    )

    with observer.trace(
        name="github-opportunity-miner.live_quality",
        input_data={"topic": topic, "profile_id": profile_label, "dynamic_search": dynamic_search},
        metadata={
            "run_id": run_id,
            "topic": topic,
            "profile_id": profile_label,
            "dynamic_search": dynamic_search,
            "validation_mode": settings.validation_mode,
            "llm_model": settings.llm_model,
            "max_issues": max_issues,
            "per_query": per_query,
        },
    ):
        state = run_graph(
            topic,
            initial_state=initial_state,
            langfuse_observer=observer,
        )

        state["langfuse_trace_url"] = observer.trace_url
        summary = quality_summary(
            state,
            topic=topic,
            profile_id=profile_label,
            artifact_dir=artifact_dir,
            started_at=started_at,
            mode="dynamic" if dynamic_search else "profile",
        )
        observer.score_run(summary)

    if observer.errors:
        state.setdefault("errors", []).extend(observer.errors)
    state["langfuse_trace_url"] = observer.trace_url
    observer.flush()
    summary = quality_summary(
        state,
        topic=topic,
        profile_id=profile_label,
        artifact_dir=artifact_dir,
        started_at=started_at,
        mode="dynamic" if dynamic_search else "profile",
    )
    diagnostics = validation_diagnostics(state)

    print(
        "GRAPH_DONE",
        "raw_issues",
        len(state.get("raw_issues") or []),
        "repos",
        [repo.get("full_name") for repo in (state.get("selected_repos") or [])],
        "errors",
        len(state.get("errors") or []),
        flush=True,
    )
    print("TOP_ISSUES", flush=True)
    for issue in (state.get("raw_issues") or [])[:8]:
        print(
            "-",
            issue.get("repo"),
            f"#{issue.get('number')}",
            str(issue.get("title", ""))[:120],
            issue.get("url"),
            flush=True,
        )

    print("VALIDATION_DIAGNOSTICS", flush=True)
    for row in diagnostics:
        print(json.dumps(row, ensure_ascii=False, sort_keys=True), flush=True)

    print("LANGFUSE_TRACE_URL", observer.trace_url or "", flush=True)
    if observer.errors:
        print("LANGFUSE_ERRORS", flush=True)
        for error in observer.errors[:5]:
            print(error, flush=True)

    if settings.validation_mode == "strict" and (state.get("rejected_cards") or []):
        print("BADCASE_SNIPPETS", flush=True)
        for snippet in badcase_snippets_from_rejections(state)[:3]:
            print(snippet, flush=True)

    artifacts = {
        "summary": summary,
        "validation_diagnostics": diagnostics,
        "profile": profile.model_dump() if profile else None,
        "search_queries": queries or state.get("global_issue_queries") or [],
        "top_issue_urls": [issue.get("url") for issue in (state.get("raw_issues") or [])[:20]],
    }
    _write_json(artifact_dir / "summary.json", summary)
    _write_json(artifact_dir / "validation_diagnostics.json", diagnostics)
    _write_json(artifact_dir / "state.json", state)
    _write_json(artifact_dir / "search_plan.json", state.get("search_plan") or {})
    _write_json(artifact_dir / "artifacts.json", artifacts)
    for key in AUDIT_ARTIFACT_KEYS:
        _write_json(artifact_dir / f"{key}.json", state.get(key) or [])
    (artifact_dir / "report.md").write_text(state.get("report_markdown") or "", encoding="utf-8")
    return state, artifact_dir, summary


def badcase_snippets_from_rejections(state: dict[str, Any]) -> list[str]:
    """Render copyable YAML snippets for rejected cards; never writes badcases."""
    snippets: list[str] = []
    evidence_by_id = {
        str(item.get("evidence_id")): item
        for item in state.get("evidence_items") or []
    }
    for card in state.get("rejected_cards") or []:
        validation = card.get("validation") or {}
        related_evidence = [
            evidence_by_id[evidence_id]
            for evidence_id in card.get("evidence_ids", [])
            if evidence_id in evidence_by_id
        ]
        snippet = {
            "id": "bc_evidence_validate_new",
            "stage": "evidence_validate",
            "failure_type": "strict_validation_rejection",
            "severity": "medium",
            "input": {
                "card": {
                    key: card.get(key)
                    for key in [
                        "opportunity_id",
                        "title",
                        "pricing_hypothesis",
                        "evidence_ids",
                        "weak_card",
                    ]
                },
                "evidence_items": [
                    {
                        "evidence_id": item.get("evidence_id"),
                        "source_url": item.get("source_url"),
                        "title": item.get("title"),
                    }
                    for item in related_evidence
                ],
                "validation_mode": "strict",
            },
            "expected": {
                "is_valid": False,
                "rejection_reasons": validation.get("rejection_reasons", []),
            },
            "actual": None,
            "fixed": False,
            "notes": "Review before adding to app/eval/badcases/evidence_validate.yaml.",
        }
        snippets.append(json.dumps(snippet, ensure_ascii=False, indent=2, sort_keys=True))
    return snippets


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a reproducible live quality audit.")
    parser.add_argument("positional_topic", nargs="?", help="Backwards-compatible topic argument")
    parser.add_argument("--topic", help="Topic for dynamic-search or profile audit runs")
    parser.add_argument("--profile", help="Benchmark profile id from topic_profiles.yaml")
    parser.add_argument("--dynamic-search", default="false", help="true to use dynamic SearchPlan instead of profile queries")
    parser.add_argument("--profiles-file", help="Path to a custom topic profiles YAML file")
    parser.add_argument("--list-profiles", action="store_true", help="List available benchmark profiles and exit")
    parser.add_argument("--per-query", type=int)
    parser.add_argument("--max-issues", type=int)
    parser.add_argument("--output-dir", default="./data/live_quality")
    parser.add_argument("--skip-debate", action="store_true")
    args = parser.parse_args()

    if args.list_profiles:
        print(json.dumps(list_profile_summaries(args.profiles_file), ensure_ascii=False, indent=2, sort_keys=True))
        return

    dynamic_search = _str_to_bool(args.dynamic_search)
    topic = args.topic or args.positional_topic or "RAG evaluation"
    if args.profile and not args.topic and not args.positional_topic and args.profile != "rag_evaluation":
        resolved = resolve_profile(topic="", profile_id=args.profile, path=args.profiles_file)
        topic = resolved.aliases[0] if resolved.aliases else resolved.label

    state, artifact_dir, summary = run_live_quality(
        topic=topic,
        per_query=args.per_query,
        max_issues=args.max_issues,
        output_dir=Path(args.output_dir),
        profile_id=args.profile,
        profiles_file=args.profiles_file,
        skip_debate=args.skip_debate,
        dynamic_search=dynamic_search,
    )

    print("QUALITY_SUMMARY", flush=True)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)

    print("VALIDATED_CARDS", flush=True)
    for card in state.get("validated_cards") or []:
        print(
            json.dumps(
                {
                    "opportunity_id": card.get("opportunity_id"),
                    "title": card.get("title"),
                    "evidence_count": len(card.get("evidence_ids") or []),
                    "evidence_urls_count": len(card.get("evidence_urls") or []),
                    "weak_card": card.get("weak_card"),
                    "source_repos": card.get("source_repos"),
                    "first_action": (card.get("validation_actions") or [""])[0],
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )

    print("FINAL_DECISIONS", flush=True)
    for decision in state.get("final_decisions") or []:
        print(
            json.dumps(
                {
                    "opportunity_id": decision.get("opportunity_id"),
                    "decision": decision.get("decision"),
                    "score": decision.get("score"),
                    "migration_cost": decision.get("migration_cost"),
                    "first_validation_action": decision.get("first_validation_action"),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )

    print("ARTIFACT_DIR", artifact_dir, flush=True)
    if state.get("errors"):
        print("FIRST_ERRORS", flush=True)
        for error in state["errors"][:10]:
            print(str(error), flush=True)


if __name__ == "__main__":
    main()
