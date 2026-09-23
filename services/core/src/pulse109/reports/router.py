"""Asynchronous-shaped report API with deterministic local rendering."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict

from pulse109.analytics.router import AnalyticsQueryRequest
from pulse109.analytics.service import AnalyticsError, AnalyticsService
from pulse109.security import AuthenticatedActor

from .models import ReportArtifact, ReportJob, ReportRequest
from .renderers import artifact_sha256, render_pdf, render_xlsx
from .service import ReportIdempotencyConflict, ReportJobStore


class PublicReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["pdf", "xlsx"]
    template_id: str
    query: AnalyticsQueryRequest
    locale: Literal["kk-KZ", "ru-KZ"] = "ru-KZ"


class ReportRuntime:
    def __init__(self, analytics: AnalyticsService) -> None:
        self.analytics = analytics
        self.jobs = ReportJobStore()
        self.artifacts: dict[UUID, ReportArtifact] = {}
        self.contents: dict[UUID, bytes] = {}
        self.access: dict[UUID, tuple[str, str]] = {}

    def create(
        self,
        command: PublicReportRequest,
        *,
        idempotency_key: str,
        region_id: str,
        actor: str,
        purpose: str,
    ) -> ReportJob:
        request = ReportRequest(
            format=command.format,
            template_id=command.template_id,
            query=command.query.internal(),
            locale=command.locale,
            purpose=purpose,
            region_id=region_id,
            actor_token=actor,
        )
        job = self.jobs.enqueue(request, idempotency_key=idempotency_key)
        self.access[job.job_id] = (region_id, actor)
        if job.status == "succeeded":
            return job
        result = self.analytics.query(request.query, actor_region=region_id)
        watermark = "SYNTHETIC / GOVERNED / NOT FOR OPERATIONAL USE"
        content = (
            render_pdf(result, watermark=watermark)
            if request.format == "pdf"
            else render_xlsx(result, watermark=watermark)
        )
        content_type: Literal[
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ] = (
            "application/pdf"
            if request.format == "pdf"
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        object_ref = f"memory://reports/{job.job_id}.{request.format}"
        artifact = ReportArtifact(
            job_id=job.job_id,
            object_ref=object_ref,
            sha256=artifact_sha256(content),
            content_type=content_type,
            metric_id=result.metric_id,
            metric_version=result.metric_version,
            data_cutoff=result.data_cutoff,
            watermark=watermark,
        )
        completed = job.model_copy(
            update={
                "status": "succeeded",
                "completed_at": datetime.now(timezone.utc),
                "result_ref": object_ref,
            }
        )
        self.jobs.jobs[job.job_id] = completed
        self.artifacts[job.job_id] = artifact
        self.contents[job.job_id] = content
        return completed


def create_report_router(runtime: ReportRuntime) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Reports"])

    @router.post("/reports", response_model=ReportJob, status_code=status.HTTP_202_ACCEPTED)
    def create_report(
        command: PublicReportRequest,
        identity: AuthenticatedActor,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
        region_id: str = Header(alias="X-Region-Id", pattern=r"^(ALL|[A-Z0-9_-]{2,32})$"),
        purpose: str = Header(default="local-synthetic-review", alias="X-Export-Purpose"),
    ) -> ReportJob:
        try:
            identity.require_any_role("analyst", "supervisor", "auditor", "admin")
            identity.require_region(region_id)
            identity.require_purpose(purpose)
            return runtime.create(
                command,
                idempotency_key=idempotency_key,
                region_id=region_id,
                actor=identity.actor_id,
                purpose=purpose,
            )
        except ReportIdempotencyConflict as error:
            raise HTTPException(
                status_code=409,
                detail={"code": "idempotency_conflict", "message": str(error)},
            ) from error
        except (AnalyticsError, ValueError) as error:
            code = error.code if isinstance(error, AnalyticsError) else "invalid_report_request"
            status_code = error.status_code if isinstance(error, AnalyticsError) else 422
            raise HTTPException(
                status_code=status_code,
                detail={"code": code, "message": str(error)},
            ) from error

    @router.get("/jobs/{job_id}", response_model=ReportJob, tags=["Operations"])
    def get_job(
        job_id: UUID,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^(ALL|[A-Z0-9_-]{2,32})$"),
    ) -> ReportJob:
        identity.require_any_role("analyst", "supervisor", "auditor", "admin")
        identity.require_region(region_id)
        job = runtime.jobs.jobs.get(job_id)
        if job is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "job_not_found", "message": "Report job not found."},
            )
        owner_region, owner_actor = runtime.access[job_id]
        identity.require_region(owner_region)
        if region_id != owner_region and region_id != "ALL":
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "region_scope_denied",
                    "message": "The report belongs to a different region scope.",
                },
            )
        if identity.actor_id != owner_actor and not identity.roles.intersection(
            {"supervisor", "auditor", "admin"}
        ):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "object_access_denied",
                    "message": "The report job belongs to a different actor.",
                },
            )
        return job

    return router
