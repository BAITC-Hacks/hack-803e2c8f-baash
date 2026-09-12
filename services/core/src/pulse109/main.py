from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text

from pulse109 import __version__
from pulse109.analytics import AlertStore, AnalyticsService, create_analytics_router
from pulse109.config import get_settings
from pulse109.database import get_engine
from pulse109.incidents import IncidentService, InMemoryIncidentRepository, create_incident_router
from pulse109.manual_path import InMemoryManualRepository, ManualPathService, create_manual_router
from pulse109.reports import ReportRuntime, create_report_router
from pulse109.retrieval import HybridRetriever, create_retrieval_router, synthetic_corpus

app = FastAPI(
    title="Pulse 109 Core API",
    version=__version__,
    docs_url="/docs" if get_settings().environment in {"local", "development", "test"} else None,
    redoc_url=None,
)

# The synthetic/manual profile remains usable while PostgreSQL and ML are unavailable.
manual_repository = InMemoryManualRepository()
app.include_router(create_manual_router(ManualPathService(manual_repository)))

retrieval_service = HybridRetriever(synthetic_corpus())
app.include_router(create_retrieval_router(retrieval_service))

incident_repository = InMemoryIncidentRepository()
app.include_router(create_incident_router(IncidentService(incident_repository, manual_repository)))

analytics_service = AnalyticsService()
alert_store = AlertStore()
alert_store.detect(
    alert_type="data_quality",
    region_id="KAR",
    metric_id="coverage",
    metric_version="1.0.0",
    severity="warning",
    detected_at=datetime(2026, 9, 10, 23, 59, tzinfo=timezone.utc),
    observed_value=None,
    baseline=None,
    evidence={"state": "missing", "source": "synthetic://m6/read-model/1.0.0"},
)
app.include_router(create_analytics_router(analytics_service, alert_store))

report_runtime = ReportRuntime(analytics_service)
app.include_router(create_report_router(report_runtime))


@app.get("/v1/health/live", tags=["Operations"], operation_id="getLiveness")
async def liveness() -> dict[str, str]:
    return {"status": "alive", "service": get_settings().service_name, "version": __version__}


@app.get("/v1/health/ready", tags=["Operations"], operation_id="getReadiness")
async def readiness() -> dict[str, Any]:
    settings = get_settings()
    if not settings.readiness_database_required:
        return {"status": "ready", "checks": {"database": "disabled-by-profile"}}

    try:
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "critical_dependency_unavailable",
                "message": "The database readiness check failed.",
            },
        ) from exc

    return {"status": "ready", "checks": {"database": "ready"}}
