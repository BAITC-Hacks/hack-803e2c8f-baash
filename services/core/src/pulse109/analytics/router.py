from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from pulse109.security import AuthenticatedActor

from .alerts import AlertStore
from .ask_models import AskDrilldownRequest, AskExportRequest, AskRequest, AskResponse
from .ask_service import AskService
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


def create_analytics_router(
    service: AnalyticsService, alerts: AlertStore, *, ask_service: AskService | None = None
) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Analytics"])
    ask_runtime = ask_service or AskService(service, alerts)

    @router.post("/analytics/ask", response_model=AskResponse, operation_id="askPulse")
    def ask_metrics(
        command: AskRequest,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^(ALL|[A-Z0-9_-]{2,32})$"),
    ) -> AskResponse:
        try:
            return ask_runtime.ask(command, identity=identity, actor_region=region_id)
        except AnalyticsError as error:
            raise HTTPException(
                status_code=error.status_code, detail={"code": error.code, "message": error.message}
            ) from error

    @router.post("/analytics/ask/export", operation_id="exportAskPulse")
    def export_ask(
        command: AskExportRequest,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^(ALL|[A-Z0-9_-]{2,32})$"),
        purpose: str = Header(
            default="synthetic-development", alias="X-Export-Purpose", max_length=256
        ),
    ) -> Response:
        from pulse109.reports.renderers import RendererUnavailable, render_pdf, render_xlsx

        identity.require_any_role("analyst", "supervisor", "auditor", "admin")
        identity.require_region(region_id)
        identity.require_purpose(purpose)
        try:
            calculated = ask_runtime.export_result(command.result_token, identity, region_id)
            synthetic = bool(getattr(calculated, "synthetic", False)) or any(
                "synthetic" in ref for ref in calculated.provenance
            )
            watermark = (
                "SYNTHETIC / GOVERNED"
                if synthetic
                else "GOVERNED / PARTIAL COVERAGE"
                if calculated.quality != "complete"
                else "GOVERNED"
            )
            content = (
                render_pdf(calculated, watermark=watermark)
                if command.format == "pdf"
                else render_xlsx(calculated, watermark=watermark)
            )
            return Response(
                content=content,
                media_type="application/pdf"
                if command.format == "pdf"
                else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f'attachment; filename="ask-pulse.{command.format}"',
                    "Cache-Control": "no-store",
                },
            )
        except AnalyticsError as error:
            raise HTTPException(
                status_code=error.status_code, detail={"code": error.code, "message": error.message}
            ) from error
        except RendererUnavailable as error:
            raise HTTPException(
                status_code=503, detail={"code": "renderer_unavailable", "message": str(error)}
            ) from error

    @router.post("/analytics/ask/drilldown", operation_id="drilldownAskPulse")
    def drilldown_ask(
        command: AskDrilldownRequest,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^(ALL|[A-Z0-9_-]{2,32})$"),
    ) -> object:
        identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
        identity.require_region(region_id)
        try:
            intent = ask_runtime.context(command.context_token, identity, region_id)
            if intent.metric_id != "appeals_volume" or intent.intent_type in {
                "forecast",
                "surge",
                "bottlenecks",
            }:
                raise AnalyticsError(
                    "DRILLDOWN_UNSUPPORTED",
                    "This capability does not expose a matching appeal drill-down.",
                )
            provider = getattr(service, "drilldown", None)
            if provider is None:
                raise AnalyticsError(
                    "drilldown_unavailable", "Underlying appeal drilldown is unavailable.", 503
                )
            from .ask_service import intent_query

            return provider(intent_query(intent), actor_region=region_id, limit=command.limit)
        except AnalyticsError as error:
            raise HTTPException(
                status_code=error.status_code, detail={"code": error.code, "message": error.message}
            ) from error

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
        return alerts.list(
            region_id=region_id,
            status=alert_status,
            from_=from_,
            to=to,
        )

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
