"""LLM runner concurrency helpers."""

from app.harness.llm_runner import LLMRunner


def test_llm_runner_preserves_input_order():
    runner = LLMRunner(max_concurrency=3)

    out = runner.run_many([3, 1, 2], lambda item: item * 10)

    assert out == [30, 10, 20]
