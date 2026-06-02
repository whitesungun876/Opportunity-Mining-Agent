"""ToolRunner with timeout, retry, partial failure, mock mode, and trace hooks."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
import time
from typing import Any, Callable

from app.harness.trace_logger import JsonTraceLogger


class ToolRunner:
    """Execute tools deterministically through shared harness behavior."""

    def __init__(
        self,
        *,
        mock_mode: bool = True,
        trace_logger: JsonTraceLogger | None = None,
        run_id: str = "local",
    ) -> None:
        self.mock_mode = mock_mode
        self.trace_logger = trace_logger
        self.run_id = run_id

    def run(
        self,
        fn: Callable[..., Any],
        *args: Any,
        timeout_seconds: int = 30,
        retry_limit: int = 2,
        node_name: str = "tool",
        allow_partial_failure: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Run a function with retry and timeout; return partial failure payload if allowed."""
        errors: list[str] = []
        start = time.perf_counter()
        for attempt in range(retry_limit + 1):
            executor = ThreadPoolExecutor(max_workers=1)
            try:
                future = executor.submit(fn, *args, **kwargs)
                result = future.result(timeout=timeout_seconds)
                latency_ms = (time.perf_counter() - start) * 1000
                self._trace(node_name, {"args": args, "kwargs": kwargs}, result, latency_ms, errors)
                return result
            except TimeoutError:
                future.cancel()
                errors.append(f"timeout after {timeout_seconds}s on attempt {attempt + 1}")
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
            finally:
                executor.shutdown(wait=False, cancel_futures=True)

        latency_ms = (time.perf_counter() - start) * 1000
        failure = {"partial_failure": True, "errors": errors, "items": []}
        self._trace(node_name, {"args": args, "kwargs": kwargs}, failure, latency_ms, errors)
        if allow_partial_failure:
            return failure
        raise RuntimeError("; ".join(errors))

    def _trace(
        self,
        node_name: str,
        input_data: Any,
        output_data: Any,
        latency_ms: float,
        errors: list[str],
    ) -> None:
        if self.trace_logger is None:
            return
        self.trace_logger.log(
            run_id=self.run_id,
            node_name=node_name,
            input_data=input_data,
            output_data=output_data,
            latency_ms=latency_ms,
            errors=errors,
            is_mock=self.mock_mode,
        )
