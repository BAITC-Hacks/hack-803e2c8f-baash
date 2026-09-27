"""Data Lab endpoints. Read-only, region-scoped, every answer carries provenance."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, status

from pulse109.security import AuthenticatedActor

from .models import (
    ArrivalSeries,
    Drilldown,
    HandoffAnalytics,
    LiveDataQuality,
    MetricDefinition,
    ProcessFunnel,
    StatusFlow,
    TimingBreakdown,
)
from .service import METRIC_VERSION, PostgresDataLabService

DEFINITIONS: tuple[MetricDefinition, ...] = (
    MetricDefinition(
        key="handoff_rate",
        title="Handoff rate",
        numerator="appeals whose assignment moved from one service to another",
        denominator="appeals in the region",
        time_basis="assignment creation order",
        included=["appeals with at least two assignments to different services"],
        excluded=[
            "appeals never assigned",
            "reassignments back to the same service, which are not a handoff",
        ],
        metric_version=METRIC_VERSION,
    ),
    MetricDefinition(
        key="time_to_first_decision",
        title="Time to first decision",
        numerator="minutes between the received time and the first operator decision",
        denominator="appeals with a decision and a trustworthy received time",
        time_basis="business time, exact or with a stated timezone assumption",
        included=["appeals whose received time quality is exact or source_tz_assumed"],
        excluded=[
            "appeals with a missing or date-only received time, because a duration "
            "measured from an invented start is not a duration"
        ],
        metric_version=METRIC_VERSION,
    ),
    MetricDefinition(
        key="verified_closed",
        title="Verified closure",
        numerator="closed appeals carrying at least one piece of evidence",
        denominator="closed appeals",
        time_basis="current status",
        included=["appeals in status closed"],
        excluded=["appeals resolved but not closed"],
        metric_version=METRIC_VERSION,
    ),
)


def create_datalab_router(service: PostgresDataLabService | None) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["DataLab"])

    def _require(service_instance: PostgresDataLabService | None) -> PostgresDataLabService:
        if service_instance is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "datalab_unavailable",
                    "message": "The data lab needs the PostgreSQL profile.",
                },
            )
        return service_instance

    def _authorize(identity: AuthenticatedActor, region_id: str) -> None:
        identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
        identity.require_region(region_id)

    @router.get("/datalab/quality", response_model=LiveDataQuality, operation_id="getDataQuality")
    def quality(
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> LiveDataQuality:
        _authorize(identity, region_id)
        return _require(service).quality(region_id=region_id)

    @router.get("/datalab/arrivals", response_model=ArrivalSeries, operation_id="getArrivals")
    def arrivals(
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        window_hours: Annotated[int, Query(ge=1, le=720)] = 24,
        bucket_minutes: Annotated[int, Query(ge=5, le=1440)] = 60,
    ) -> ArrivalSeries:
        _authorize(identity, region_id)
        return _require(service).arrivals(
            region_id=region_id, window_hours=window_hours, bucket_minutes=bucket_minutes
        )

    @router.get("/datalab/process", response_model=ProcessFunnel, operation_id="getProcessFunnel")
    def funnel(
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> ProcessFunnel:
        _authorize(identity, region_id)
        return _require(service).funnel(region_id=region_id)

    @router.get("/datalab/status-flow", response_model=StatusFlow, operation_id="getStatusFlow")
    def status_flow(
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> StatusFlow:
        _authorize(identity, region_id)
        return _require(service).status_flow(region_id=region_id)

    @router.get("/datalab/timings", response_model=list[TimingBreakdown], operation_id="getTimings")
    def timings(
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> list[TimingBreakdown]:
        _authorize(identity, region_id)
        return _require(service).timings(region_id=region_id)

    @router.get(
        "/datalab/handoffs", response_model=HandoffAnalytics, operation_id="getHandoffAnalytics"
    )
    def handoffs(
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> HandoffAnalytics:
        _authorize(identity, region_id)
        return _require(service).handoffs(region_id=region_id)

    @router.get("/datalab/drilldown", response_model=Drilldown, operation_id="getDrilldown")
    def drilldown(
        identity: AuthenticatedActor,
        key: Annotated[str, Query(max_length=256, pattern=r"^[a-z_]+:[A-Za-z0-9_.:>-]+$")],
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> Drilldown:
        """Open an aggregate and read the appeals behind it.

        The key is matched against a closed mapping in the service. It never
        reaches SQL as text, because an analytics filter is exactly where
        somebody would try to reach the database.
        """
        _authorize(identity, region_id)
        return _require(service).drilldown(region_id=region_id, key=key, limit=limit)

    @router.get(
        "/datalab/definitions",
        response_model=list[MetricDefinition],
        operation_id="getMetricDefinitions",
    )
    def definitions(identity: AuthenticatedActor) -> list[MetricDefinition]:
        """What each metric counts, and what it leaves out."""
        identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
        return list(DEFINITIONS)

    return router


__all__ = ["DEFINITIONS", "create_datalab_router"]
