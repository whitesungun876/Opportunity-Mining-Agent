"""Real pain extractor schema parsing tests without a real LLM call."""

from app.nodes.pain_extract import parse_pain_extractor_response


def test_parse_pain_extractor_response_normalizes_schema():
    issue = {
        "issue_id": "ev_789",
        "evidence_id": "ev_789",
        "title": "Need production eval dashboard",
        "body": "We need to replay bad cases before every release.",
    }
    fake_response = {
        "pain_id": "pain_789",
        "evidence_id": "ev_789",
        "pain_type": "evaluation_gap",
        "complaint": "Teams cannot replay bad cases before release.",
        "persona": "AI platform engineer",
        "context": "pre-release RAG evaluation",
        "severity": 0.86,
        "workaround": "manual spreadsheets",
        "business_signal": "Potential demand for hosted evaluation dashboard",
        "supporting_quote": "We need to replay bad cases before every release.",
    }

    parsed = parse_pain_extractor_response(fake_response, issue)

    assert parsed["pain_id"] == "pain_789"
    assert parsed["evidence_id"] == "ev_789"
    assert parsed["evidence_ids"] == ["ev_789"]
    assert parsed["pain_type"] == "evaluation_gap"
    assert parsed["severity"] == 0.86
    assert parsed["supporting_quote"] in issue["body"]


def test_parse_pain_extractor_response_replaces_ungrounded_quote():
    issue = {
        "issue_id": "ev_790",
        "evidence_id": "ev_790",
        "title": "Production deployment is blocked",
        "body": "The fake quote is not here.",
    }
    parsed = parse_pain_extractor_response(
        {
            "evidence_id": "ev_790",
            "pain_type": "not_a_type",
            "severity": 2.0,
            "supporting_quote": "Invented quote",
        },
        issue,
    )

    assert parsed["pain_type"] == "unclear"
    assert parsed["severity"] == 1.0
    assert parsed["supporting_quote"] == issue["title"]
