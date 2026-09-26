from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from pulse109.security import AuthenticatedActor

from .alerts import AlertStore
from .models import Alert, AlertReview, AnalyticsQuery, AnalyticsResult, MetricFilter
from .service import AnalyticsError, AnalyticsService


class AlertReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["acknowledge", "resolve", "dismiss"]
    disposition: Annotated[str, Field(min_length=1, max_length=256)]
    evidence_refs: list[Annotated[str, Field(min_length=1, max_length=256)]] = Field(
        default_factory=list
    )


class TimeRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_: datetime = Field(alias="from")
    to: datetime


class AnalyticsQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: Literal["appeals_volume", "sla_risk", "source_freshness", "coverage"]
    dimensions: list[str] = Field(default_factory=list, max_length=5)
    filters: dict[str, list[str]] = Field(default_factory=dict)
    time_range: TimeRange
    granularity: Literal["hour", "day", "week", "month"] = "day"
    limit: int = Field(default=1000, ge=1, le=5000)

    def internal(self) -> AnalyticsQuery:
        return AnalyticsQuery(
            metric_id=self.metric_id,
            dimensions=self.dimensions,
            filters=[
                MetricFilter(field=name, operator="in", value=values)
                for name, values in self.filters.items()
            ],
            time_from=self.time_range.from_,
            time_to=self.time_range.to,
            granularity=self.granularity,
            limit=self.limit,
        )


def create_analytics_router(service: AnalyticsService, alerts: AlertStore) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Analytics"])

    @router.post("/analytics/query", response_model=AnalyticsResult)
    def query_metrics(
        command: AnalyticsQueryRequest,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^(ALL|[A-Z0-9_-]{2,32})$"),
    ) -> AnalyticsResult:
        identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
        identity.require_region(region_id)
        try:
            return service.query(command.internal(), actor_region=region_id)
        except AnalyticsError as error:
            raise HTTPException(
                status_code=error.status_code,
                detail={"code": error.code, "message": error.message},
            ) from error

    @router.get("/alerts", response_model=list[Alert])
    def list_alerts(
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^(ALL|[A-Z0-9_-]{2,32})$"),
        alert_status: Annotated[
            Literal["new", "acknowledged", "resolved", "dismissed"] | None,
            Query(alias="status"),
        ] = None,
        from_: Annotated[datetime | None, Query(alias="from")] = None,
        to: Annotated[datetime | None, Query()] = None,
    ) -> list[Alert]:
        identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
        identity.require_region(region_id)
        values = list(alerts.alerts.values())
        return [
            item
            for item in values
            if (region_id == "ALL" or item.region_id == region_id)
            and (alert_status is None or item.status == alert_status)
            and (from_ is None or item.detected_at >= from_)
            and (to is None or item.detected_at <= to)
        ]

    @router.post("/alerts/{alert_id}/reviews", response_model=Alert)
    def review_alert(
        alert_id: UUID,
        command: AlertReviewInput,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^(ALL|[A-Z0-9_-]{2,32})$"),
    ) -> Alert:
        identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
        identity.require_region(region_id)
        current = alerts.get(alert_id)
        if current is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        if region_id != "ALL" and current.region_id != region_id:
            raise HTTPException(status_code=403, detail="Alert belongs to another region")
        review = AlertReview(
            alert_id=alert_id,
            actor_token=identity.actor_id,
            action=command.action,
            disposition=command.disposition,
            evidence_refs=command.evidence_refs,
            reviewed_at=datetime.now(timezone.utc),
        )
        try:
            return alerts.review(review)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    return router
