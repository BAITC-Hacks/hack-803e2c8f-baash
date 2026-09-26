"""Authenticated Replay Lab inspection API."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from pulse109.security import AuthenticatedActor

from .engine import ReplayReport
from .persistence import ReplayRepository


class ReplayReportSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str
    dataset_id: str
    region_id: str
    cutoff_at: str
    baseline_policy_id: str
    baseline_version: str
    candidate_policy_id: str
    candidate_version: str
    created_at: str
    decision: str | None = None


def create_replay_router(
    repository: ReplayRepository | None,
    *,
    allow_synthetic: bool = False,
) -> APIRouter:
    router = APIRouter(prefix="/v1/replay", tags=["Replay Lab"])

    def _require_supervisor(identity: AuthenticatedActor, region_id: str) -> None:
        identity.require_any_role("admin", "supervisor")
        identity.require_region(region_id)
        if repository is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "replay_unavailable",
                    "message": "Durable Replay Lab storage is unavailable.",
                },
            )

    @router.get(
        "/reports",
        response_model=list[ReplayReportSummary],
        operation_id="listReplayReports",
    )
    def list_reports(
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        limit: int = Query(default=20, ge=1, le=100),
    ) -> list[ReplayReportSummary]:
        _require_supervisor(identity, region_id)
        assert repository is not None
        rows = repository.list_reports(region_id=region_id, limit=limit)
        return [ReplayReportSummary.model_validate(row) for row in rows]

    @router.get(
        "/reports/{report_id}",
        response_model=ReplayReport,
        operation_id="getReplayReport",
    )
    def get_report(
        report_id: str,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> ReplayReport:
        _require_supervisor(identity, region_id)
        assert repository is not None
        report = repository.get_report(report_id, region_id=region_id)
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "report_not_found", "message": "Replay report not found."},
            )
        return report

    return router
