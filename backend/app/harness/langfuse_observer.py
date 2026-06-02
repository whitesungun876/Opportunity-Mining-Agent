"""Optional Langfuse observer for live eval runs."""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
import os
import time
from typing import Any, Iterator

from app.config import Settings


def _summary(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        out: dict[str, Any] = {"keys": sorted(value.keys())[:20]}
        for key, item in value.items():
            if isinstance(item, list):
                out[f"{key}_count"] = len(item)
        return out
    if isinstance(value, list):
        return {"count": len(value)}
    return {"repr": str(value)[:240]}


def score_payload(summary: dict[str, Any]) -> dict[str, Any]:
    opportunity_count = int(summary.get("opportunity_cards") or 0)
    validated_count = int(summary.get("validated_cards") or 0)
    errors = int(summary.get("errors") or 0)
    return {
        "validated_cards": float(validated_count),
        "rejected_cards": float(summary.get("rejected_cards") or 0),
        "validated_rate": float(validated_count / max(1, opportunity_count)),
        "high_value_issues": float(summary.get("high_value_issues") or 0),
        "pain_points": float(summary.get("pain_points") or 0),
        "error_count": float(errors),
        "strict_pass": 1.0 if validated_count > 0 and errors == 0 else 0.0,
        "report_has_github": 1.0 if summary.get("report_has_github") else 0.0,
    }


class LangfuseObserver:
    """Thin compatibility layer around Langfuse v3's current-observation API."""

    def __init__(self, settings: Settings) -> None:
        self.enabled = bool(settings.langfuse_enabled)
        self.release = settings.langfuse_release
        self.environment = settings.langfuse_environment
        self.client: Any | None = None
        self.trace_url: str | None = None
        self.errors: list[str] = []
        if not self.enabled:
            return
        if settings.langfuse_base_url:
            os.environ.setdefault("LANGFUSE_BASE_URL", settings.langfuse_base_url)
        try:
            from langfuse import get_client

            self.client = get_client()
        except Exception as exc:  # pragma: no cover - depends on optional SDK/env
            self.enabled = False
            self.errors.append(f"Langfuse disabled: {type(exc).__name__}: {exc}")

    @contextmanager
    def trace(self, *, name: str, input_data: dict[str, Any], metadata: dict[str, Any]) -> Iterator[None]:
        if not self.enabled or self.client is None:
            yield
            return
        try:
            context = self.client.start_as_current_observation(
                as_type="span",
                name=name,
                input=input_data,
                metadata={**metadata, "release": self.release, "environment": self.environment},
            )
        except Exception as exc:  # pragma: no cover - network/sdk dependent
            self.errors.append(f"Langfuse trace failed: {type(exc).__name__}: {exc}")
            yield
            return
        with context as span:
            try:
                yield
            finally:
                self.trace_url = self._trace_url()
                span.update(output={"trace_url": self.trace_url})

    @contextmanager
    def node_span(
        self,
        *,
        node_name: str,
        input_data: dict[str, Any],
        output_capture: dict[str, Any] | None = None,
    ) -> Iterator[None]:
        if not self.enabled or self.client is None:
            with nullcontext():
                yield
            return
        start = time.perf_counter()
        try:
            context = self.client.start_as_current_observation(
                as_type="span",
                name=node_name,
                input=_summary(input_data),
                metadata={"node_name": node_name, "release": self.release, "environment": self.environment},
            )
        except Exception as exc:  # pragma: no cover - network/sdk dependent
            self.errors.append(f"Langfuse span {node_name} failed: {type(exc).__name__}: {exc}")
            yield
            return
        with context as span:
            try:
                yield
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                output: dict[str, Any] = {"latency_ms": latency_ms}
                metadata: dict[str, Any] = {"latency_ms": latency_ms}
                if output_capture:
                    if "output" in output_capture:
                        output["output_summary"] = _summary(output_capture["output"])
                    errors = output_capture.get("errors") or []
                    if errors:
                        output["errors"] = errors[:5]
                        metadata["error_count"] = len(errors)
                span.update(output=output, metadata=metadata)
            except Exception as exc:
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                span.update(
                    level="ERROR",
                    status_message=f"{type(exc).__name__}: {exc}",
                    metadata={"latency_ms": latency_ms},
                )
                raise

    def score_run(self, summary: dict[str, Any]) -> None:
        if not self.enabled or self.client is None:
            return
        for name, value in score_payload(summary).items():
            try:
                self.client.score_current_trace(
                    name=name,
                    value=float(value),
                    data_type="NUMERIC",
                    comment="live_quality run score",
                )
            except Exception as exc:  # pragma: no cover - network/sdk dependent
                self.errors.append(f"Langfuse score {name} failed: {type(exc).__name__}: {exc}")

    def flush(self) -> None:
        if self.enabled and self.client is not None:
            try:
                self.client.flush()
            except Exception as exc:  # pragma: no cover - network/sdk dependent
                self.errors.append(f"Langfuse flush failed: {type(exc).__name__}: {exc}")

    def _trace_url(self) -> str | None:
        if self.client is None:
            return None
        try:
            return self.client.get_trace_url()
        except Exception:
            return None
