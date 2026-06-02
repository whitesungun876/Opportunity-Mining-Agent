"""Run curated badcase regression checks for quality-critical stages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import yaml

from app.nodes.evidence_validate import validate_card_deterministic
from app.nodes.final_judge import parse_final_judge_response
from app.fusion.fusion_validator import validate_fusion_candidate
from app.nodes.issue_classify import classify_issue
from app.nodes.opportunity_generate import dedupe_opportunity_cards, parse_opportunity_card_response
from app.nodes.report_write import _render_real_report


BADCASE_DIR = Path(__file__).resolve().parent / "badcases"
STAGES = {"issue_classify", "evidence_validate", "opportunity_generate", "final_judge", "fusion_generate"}


def _json_default(value: Any) -> str:
    return str(value)


def _load_badcases(badcase_dir: Path, stage: str | None = None) -> list[dict[str, Any]]:
    paths = [badcase_dir / f"{stage}.yaml"] if stage else sorted(badcase_dir.glob("*.yaml"))
    cases: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Badcase file not found: {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for item in data.get("badcases") or []:
            cases.append(item)
    return cases


def _contains(items: list[str], needle: str) -> bool:
    return any(needle in item for item in items)


def _check_expectations(actual: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for key, expected_value in expected.items():
        if key == "decision_not":
            if actual.get("decision") == expected_value:
                failures.append(f"decision must not be {expected_value!r}")
        elif key == "unsupported_claim_contains":
            claims = actual.get("unsupported_claims") or []
            if not _contains([str(item) for item in claims], str(expected_value)):
                failures.append(f"unsupported_claims must contain {expected_value!r}")
        elif key == "pricing_contains":
            if str(expected_value) not in str(actual.get("pricing_hypothesis", "")):
                failures.append(f"pricing_hypothesis must contain {expected_value!r}")
        elif key == "rejection_contains":
            reasons = actual.get("rejection_reasons") or []
            if not _contains([str(item) for item in reasons], str(expected_value)):
                failures.append(f"rejection_reasons must contain {expected_value!r}")
        elif actual.get(key) != expected_value:
            failures.append(f"{key}: expected {expected_value!r}, got {actual.get(key)!r}")
    return failures


def _run_issue_classify(case: dict[str, Any]) -> dict[str, Any]:
    actual = classify_issue(case.get("input") or {})
    return {
        "value_level": actual.get("value_level"),
        "should_extract_pain": actual.get("should_extract_pain"),
        "category": actual.get("category"),
        "reason": actual.get("reason"),
    }


def _run_evidence_validate(case: dict[str, Any]) -> dict[str, Any]:
    payload = case.get("input") or {}
    evidence_items = payload.get("evidence_items") or []
    evidence_by_id = {str(item.get("evidence_id")): item for item in evidence_items}
    checked = validate_card_deterministic(
        payload.get("card") or {},
        evidence_by_id,
        validation_mode=payload.get("validation_mode") or "strict",
    )
    validation = checked.get("validation") or {}
    report = _render_real_report(
        {
            "validated_cards": [checked] if validation.get("is_valid") else [],
            "rejected_cards": [] if validation.get("is_valid") else [checked],
            "evidence_items": evidence_items,
            "agent_reviews": [],
            "final_decisions": [],
            "errors": [],
        }
    )
    return {
        "is_valid": validation.get("is_valid"),
        "weak_card": checked.get("weak_card"),
        "evidence_count": validation.get("evidence_count"),
        "unsupported_claims": validation.get("unsupported_claims") or [],
        "rejection_reasons": validation.get("rejection_reasons") or [],
        "in_report": str((payload.get("card") or {}).get("title") or "") in report,
    }


def _run_opportunity_generate(case: dict[str, Any]) -> dict[str, Any]:
    payload = case.get("input") or {}
    mode = payload.get("mode")
    if mode == "dedupe_cards":
        cards = payload.get("cards") or []
        deduped = dedupe_opportunity_cards(cards)
        return {
            "deduped_count": len(deduped),
            "duplicate_removed": len(deduped) < len(cards),
        }
    card = parse_opportunity_card_response(
        payload.get("response") or {},
        payload.get("gap") or {},
        state=None,
    )
    return {
        "pricing_hypothesis": card.get("pricing_hypothesis"),
        "weak_card": card.get("weak_card"),
        "evidence_count": len(card.get("evidence_ids") or []),
    }


def _run_final_judge(case: dict[str, Any]) -> dict[str, Any]:
    payload = case.get("input") or {}
    decision = parse_final_judge_response(payload.get("response") or {}, payload.get("card") or {})
    return {
        "opportunity_id": decision.get("opportunity_id"),
        "decision": decision.get("decision"),
        "score": decision.get("score"),
        "migration_cost": decision.get("migration_cost"),
    }


def _run_fusion_generate(case: dict[str, Any]) -> dict[str, Any]:
    payload = case.get("input") or {}
    checked = validate_fusion_candidate(
        payload.get("candidate") or {},
        {"evidence_items": payload.get("evidence_items") or []},
    )
    validation = checked.get("validation") or {}
    return {
        "is_valid": validation.get("is_valid"),
        "rejection_reasons": validation.get("rejection_reasons") or [],
    }


def run_badcase(case: dict[str, Any]) -> dict[str, Any]:
    stage = case.get("stage")
    if stage == "issue_classify":
        actual = _run_issue_classify(case)
    elif stage == "evidence_validate":
        actual = _run_evidence_validate(case)
    elif stage == "opportunity_generate":
        actual = _run_opportunity_generate(case)
    elif stage == "final_judge":
        actual = _run_final_judge(case)
    elif stage == "fusion_generate":
        actual = _run_fusion_generate(case)
    else:
        actual = {}
        failures = [f"Unsupported stage: {stage}"]
        return {**case, "actual": actual, "passed": False, "failures": failures}

    failures = _check_expectations(actual, case.get("expected") or {})
    return {
        "id": case.get("id"),
        "stage": stage,
        "failure_type": case.get("failure_type"),
        "severity": case.get("severity"),
        "passed": not failures,
        "failures": failures,
        "actual": actual,
    }


def run_badcases(*, stage: str | None = None, badcase_dir: Path = BADCASE_DIR) -> dict[str, Any]:
    if stage and stage not in STAGES:
        raise ValueError(f"Unsupported stage: {stage}")
    cases = _load_badcases(badcase_dir, stage)
    results = [run_badcase(case) for case in cases]
    failed = [item for item in results if not item["passed"]]
    return {
        "total": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "stage": stage or "all",
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run badcase regression checks.")
    parser.add_argument("--stage", choices=sorted(STAGES), help="Run only one badcase stage")
    parser.add_argument("--badcase-dir", default=str(BADCASE_DIR))
    parser.add_argument("--output", default="./data/badcase_results.json")
    args = parser.parse_args()

    result = run_badcases(stage=args.stage, badcase_dir=Path(args.badcase_dir))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ["total", "passed", "failed", "stage"]}, ensure_ascii=False, sort_keys=True))
    print("BADCASE_RESULTS", output_path)
    if result["failed"]:
        for item in result["results"]:
            if not item["passed"]:
                print(json.dumps(item, ensure_ascii=False, sort_keys=True))
        sys.exit(1)


if __name__ == "__main__":
    main()
