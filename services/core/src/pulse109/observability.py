"""PII-safe OpenTelemetry setup and correlation propagation."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.sdk.resources import (
    DEPLOYMENT_ENVIRONMENT,
    SERVICE_NAME,
    SERVICE_VERSION,
    Resource,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from pulse109 import __version__
from pulse109.config import Settings

_CORRELATION_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
_SAFE_LOG_FIELDS = frozenset(
    {
        "action",
        "actor_type",
        "attempt",
        "correlation_id",
        "error_code",
        "event_type",
        "latency_ms",
        "model_version",
        "region_id",
        "service",
        "status",
        "trace_id",
    }
)


class JsonFormatter(logging.Formatter):
    """Serialize only explicitly supplied safe fields."""

    def format(self, record: logging.LogRecord) -> str:
        document: dict[str, object] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        safe = getattr(record, "safe_fields", {})
        if isinstance(safe, dict):
            document.update({key: value for key, value in safe.items() if key in _SAFE_LOG_FIELDS})
        return json.dumps(document, default=str, ensure_ascii=True, separators=(",", ":"))


def log_safe(logger: logging.Logger, level: int, message: str, **fields: object) -> None:
    rejected = set(fields).difference(_SAFE_LOG_FIELDS)
    if rejected:
        raise ValueError(f"unsafe or unbounded log fields: {sorted(rejected)}")
    logger.log(level, message, extra={"safe_fields": fields})


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Return a bounded correlation ID and record low-cardinality request metrics."""

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        meter = metrics.get_meter("pulse109.http")
        self.request_count = meter.create_counter("pulse109.http.requests")
        self.request_duration = meter.create_histogram("pulse109.http.duration", unit="ms")

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        supplied = request.headers.get("X-Correlation-Id")
        if supplied is not None and not _CORRELATION_RE.fullmatch(supplied):
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "code": "invalid_correlation_id",
                        "message": "X-Correlation-Id must be 8-128 safe characters.",
                    }
                },
            )
        correlation_id = supplied or str(uuid4())
        request.state.correlation_id = correlation_id
        span = trace.get_current_span()
        span.set_attribute("pulse109.correlation_id", correlation_id)
        started = perf_counter()
        response = await call_next(request)
        duration_ms = (perf_counter() - started) * 1000
        attributes: dict[str, str | int] = {
            "http.request.method": request.method,
            "http.response.status_code": response.status_code,
        }
        self.request_count.add(1, attributes)
        self.request_duration.record(duration_ms, attributes)
        response.headers["X-Correlation-Id"] = correlation_id
        return response


def configure_observability(app: FastAPI, settings: Settings) -> None:
    """Instrument an app without making an exporter part of readiness."""

    if not settings.otel_enabled:
        app.add_middleware(CorrelationMiddleware)
        return
    provider = TracerProvider(
        resource=Resource.create(
            {
                SERVICE_NAME: settings.service_name,
                SERVICE_VERSION: __version__,
                DEPLOYMENT_ENVIRONMENT: settings.environment,
            }
        ),
        sampler=ParentBased(TraceIdRatioBased(settings.otel_sample_ratio)),
    )
    if settings.otel_exporter_endpoint:
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint))
        )
    if isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
        trace.set_tracer_provider(provider)
    # A generic span name avoids request IDs or citizen-supplied paths in
    # telemetry and handles unmatched methods without router introspection.
    app.add_middleware(
        OpenTelemetryMiddleware,
        tracer_provider=provider,
        excluded_urls="/v1/health/live,/v1/health/ready",
        default_span_details=lambda scope: (f"HTTP {scope.get('method', 'UNKNOWN')}", {}),
    )
    app.add_middleware(CorrelationMiddleware)
