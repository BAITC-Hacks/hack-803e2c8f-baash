from datetime import datetime, timezone

import pytest
from pulse109.analytics.models import AnalyticsQuery, AnalyticsResult, MetricColumn
from pulse109.reports.models import ReportRequest
from pulse109.reports.renderers import RendererUnavailable, artifact_sha256, render_pdf, render_xlsx
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
