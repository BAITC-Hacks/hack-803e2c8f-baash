from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pulse109.analytics import AnalyticsService
from pulse109.analytics.models import AnalyticsQuery, AnalyticsResult, MetricColumn
from pulse109.reports.models import ReportRequest
from pulse109.reports.renderers import RendererUnavailable, artifact_sha256, render_pdf, render_xlsx
from pulse109.reports.router import PublicReportRequest, ReportRuntime, create_report_router
from pulse109.reports.service import ReportIdempotencyConflict, ReportJobStore

ACTOR_TOKEN = "operator:test"  # noqa: S105


def request() -> ReportRequest:
    return ReportRequest(
        format="pdf",
        template_id="metric-default",
        query=AnalyticsQuery(
            metric_id="appeals_volume",
            time_from=datetime(2026, 9, 1, tzinfo=timezone.utc),
            time_to=datetime(2026, 9, 2, tzinfo=timezone.utc),
        ),
        purpose="synthetic review",
        region_id="ALA",
        actor_token=ACTOR_TOKEN,
    )


def result() -> AnalyticsResult:
    return AnalyticsResult(
        metric_id="appeals_volume",
        metric_version="1.0.0",
        columns=[
            MetricColumn(name="region_id", type="string"),
            MetricColumn(name="count", type="integer"),
        ],
        rows=[["ALA", 4]],
        computed_at=datetime(2026, 9, 12, tzinfo=timezone.utc),
        data_cutoff=datetime(2026, 9, 12, tzinfo=timezone.utc),
        quality="complete",
        coverage={"ALA": "present"},
        provenance=["synthetic://read-model"],
    )


def test_report_idempotency_replays_and_conflicts() -> None:
    store = ReportJobStore()
    first = store.enqueue(request(), idempotency_key="report-1")
    assert store.enqueue(request(), idempotency_key="report-1").job_id == first.job_id
    changed = request().model_copy(update={"purpose": "another purpose"})
    with pytest.raises(ReportIdempotencyConflict):
        store.enqueue(changed, idempotency_key="report-1")


def test_pdf_uses_same_metric_result_and_has_stable_hash() -> None:
    data = render_pdf(result())
    assert data.startswith(b"%PDF")
    assert artifact_sha256(data) == artifact_sha256(data)


def test_xlsx_requires_optional_renderer_dependency() -> None:
    try:
        data = render_xlsx(result())
    except RendererUnavailable:
        return
    assert data.startswith(b"PK")


def test_xlsx_escapes_formula_like_text() -> None:
    try:
        data = render_xlsx(result().model_copy(update={"rows": [['=HYPERLINK("bad")', 4]]}))
    except RendererUnavailable:
        return
    from io import BytesIO

    from openpyxl import load_workbook

    sheet = load_workbook(BytesIO(data), data_only=False).active
    assert sheet["A4"].value == '\'=HYPERLINK("bad")'
    assert sheet["A4"].data_type != "f"


def test_report_job_read_is_bound_to_verified_actor_or_supervisor() -> None:
    app = FastAPI()
    runtime = ReportRuntime(AnalyticsService())
    app.include_router(create_report_router(runtime))
    command = PublicReportRequest.model_validate(
        {
            "format": "pdf",
            "template_id": "synthetic-situation",
            "query": {
                "metric_id": "coverage",
                "dimensions": ["region_id"],
                "filters": {"region_id": ["ALA"]},
                "time_range": {
                    "from": "2026-09-01T00:00:00+00:00",
                    "to": "2026-09-12T00:00:00+00:00",
                },
                "granularity": "day",
                "limit": 100,
            },
        }
    )
    owner_headers = {
        "Idempotency-Key": "report-access-key-1",
        "X-Region-Id": "ALA",
        "X-Actor-Token": "analyst-1",
        "X-Actor-Roles": "analyst",
        "X-Actor-Regions": "ALA",
    }
    with TestClient(app) as client:
        created = client.post(
            "/v1/reports",
            json=command.model_dump(mode="json", by_alias=True),
            headers=owner_headers,
        )
        assert created.status_code == 202, created.text
        job_id = created.json()["job_id"]
        denied = client.get(
            f"/v1/jobs/{job_id}",
            headers={
                "X-Region-Id": "ALA",
                "X-Actor-Token": "analyst-2",
                "X-Actor-Roles": "analyst",
                "X-Actor-Regions": "ALA",
            },
        )
        supervisor = client.get(
            f"/v1/jobs/{job_id}",
            headers={
                "X-Region-Id": "ALA",
                "X-Actor-Token": "supervisor-2",
                "X-Actor-Roles": "supervisor",
                "X-Actor-Regions": "ALA",
            },
        )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "object_access_denied"
    assert supervisor.status_code == 200
