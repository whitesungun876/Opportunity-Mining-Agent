"""评估指标单元测试。"""

import pytest
from src.eval.metrics import (
    rejection_rate,
    denoise_ratio,
    schema_compliance_rate,
    compute_run_metrics,
)


def test_rejection_rate():
    assert rejection_rate(8, 10) == pytest.approx(0.2)
    assert rejection_rate(0, 10) == 1.0
    assert rejection_rate(10, 0) == 0.0


def test_denoise_ratio():
    assert denoise_ratio(10, 5) == 0.5
    assert denoise_ratio(0, 0) == 1.0


def test_schema_compliance_rate():
    assert schema_compliance_rate(9, 10) == 0.9
    assert schema_compliance_rate(0, 0) == 1.0


def test_compute_run_metrics():
    state = {
        "raw_items": [1, 2, 3, 4, 5],
        "cleaned_texts": ["a", "b", "c"],
        "opportunities": [{"id": "1"}, {"id": "2"}],
        "validated_opportunities": [{"id": "1"}],
    }
    m = compute_run_metrics(state)
    assert m["denoise_ratio"] == 3 / 5
    assert m["rejection_rate"] == 0.5
    assert m["opportunities_count"] == 2
    assert m["validated_count"] == 1
