from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.base import RequestResponseEndpoint

from pulse109 import __version__
from pulse109.analytics import AlertStore, AnalyticsService, create_analytics_router
from pulse109.catalog import PolicyService, create_catalog_router
from pulse109.config import get_settings
from pulse109.database import get_engine
from pulse109.decisions.publication import ConfidencePublicationService
from pulse109.decisions.publication_router import create_confidence_publication_router
from pulse109.incidents import (
    IncidentService,
    InMemoryIncidentRepository,
    PostgresIncidentRepository,
    PostgresIncidentService,
    create_incident_router,
)
from pulse109.intake import (
    EmptyIntakePolicyRepository,
    IntakeApplicationService,
    PostgresIntakePolicyRepository,
    create_intake_router,
)
from pulse109.manual_path import (
    InMemoryManualRepository,
    ManualPathService,
    PostgresManualPathService,
    PostgresManualRepository,
    create_manual_router,
)
from pulse109.observability import configure_observability
from pulse109.outcomes import (
    ClosureIntegrityService,
    PostgresClosureRepository,
    create_closure_router,
)
from pulse109.ownership.outcomes import HandoffOutcomeService
from pulse109.ownership.repository import EmptyOwnershipRepository, PostgresOwnershipRepository
from pulse109.ownership.router import create_ownership_router
from pulse109.ownership.service import OwnershipService
from pulse109.reports import ReportRuntime, create_report_router
from pulse109.retrieval import HybridRetriever, create_retrieval_router, synthetic_corpus

app = FastAPI(
    title="Pulse 109 Core API",
    version=__version__,
    docs_url="/docs" if get_settings().environment in {"local", "development", "test"} else None,
    redoc_url=None,
)
configure_observability(app, get_settings())

# Memory is an explicit local/test fallback. Pilot and production always use PostgreSQL.
settings = get_settings()
use_postgres_manual_path = settings.environment in {"pilot", "production"} or (
    settings.manual_repository_mode == "postgres"
)
manual_repository: InMemoryManualRepository | PostgresManualRepository
manual_service: ManualPathService | PostgresManualPathService
if use_postgres_manual_path:
    manual_repository = PostgresManualRepository(settings.database_url)
    manual_service = PostgresManualPathService(manual_repository)
else:
    manual_repository = InMemoryManualRepository()
    manual_service = ManualPathService(manual_repository)
app.include_router(create_manual_router(manual_service))
intake_repository = (
    PostgresIntakePolicyRepository(settings.database_url)
    if use_postgres_manual_path
    else EmptyIntakePolicyRepository()
)
app.include_router(
    create_intake_router(
        IntakeApplicationService(
            intake_repository,
            allow_synthetic=settings.environment in {"local", "development", "test"},
        )
    )
)
ownership_repository: PostgresOwnershipRepository | EmptyOwnershipRepository
handoff_service: HandoffOutcomeService | None
if use_postgres_manual_path:
    ownership_repository = PostgresOwnershipRepository(settings.database_url)
    handoff_service = HandoffOutcomeService(ownership_repository)
else:
    ownership_repository = EmptyOwnershipRepository()
    handoff_service = None
app.include_router(
    create_ownership_router(
        manual_service,
        OwnershipService(
            ownership_repository,
            allow_synthetic=settings.environment in {"local", "development", "test"},
        ),
        handoff_service,
    )
)
app.include_router(
    create_catalog_router(
        PolicyService(settings.database_url if use_postgres_manual_path else None)
    )
)
app.include_router(
    create_confidence_publication_router(
        ConfidencePublicationService(
            settings.database_url,
            allow_synthetic=settings.environment in {"local", "development", "test"},
        )
        if use_postgres_manual_path
        else None
    )
)
app.include_router(
    create_closure_router(
        ClosureIntegrityService(PostgresClosureRepository(settings.database_url))
        if use_postgres_manual_path
        else None
    )
)

synthetic_read_models = settings.environment in {"local", "development", "test"}
retrieval_service = HybridRetriever(synthetic_corpus() if synthetic_read_models else [])
app.include_router(create_retrieval_router(retrieval_service))

if use_postgres_manual_path:
    postgres_incident_repository = PostgresIncidentRepository(settings.database_url)
    incident_repository: InMemoryIncidentRepository | PostgresIncidentRepository = (
        postgres_incident_repository
    )
    incident_service: IncidentService | PostgresIncidentService = PostgresIncidentService(
        postgres_incident_repository
    )
else:
    incident_repository = InMemoryIncidentRepository()
    incident_service = IncidentService(incident_repository, manual_repository)
app.include_router(create_incident_router(incident_service))

analytics_service = AnalyticsService(synthetic=synthetic_read_models)
alert_store = AlertStore()
if synthetic_read_models:
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


@app.middleware("http")
async def unavailable_synthetic_read_models(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    """Do not expose demo corpus or volatile report state in operational profiles."""
    path = request.url.path
    demo_route = (
        path in {"/v1/analytics/query", "/v1/alerts", "/v1/reports", "/v1/appeals/preflight"}
        or path.startswith("/v1/jobs/")
        or (
            path.startswith("/v1/requests/")
            and path.endswith(("/similar", "/duplicate-candidates"))
        )
    )
    if not synthetic_read_models and demo_route:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": {
                    "code": "read_model_unavailable",
                    "message": "An approved durable read model is not configured for this profile.",
                }
            },
        )
    return await call_next(request)


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
