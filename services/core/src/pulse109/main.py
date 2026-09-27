import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.base import RequestResponseEndpoint

from pulse109 import __version__
from pulse109.analytics import (
    AlertStore,
    AnalyticsService,
    PostgresAlertStore,
    create_analytics_router,
)
from pulse109.catalog import PolicyService, create_catalog_router
from pulse109.config import Settings, get_settings
from pulse109.control_plane import (
    BundleRepository,
    BundleVerifier,
    MemoryBundleRepository,
    PostgresBundleRepository,
    create_control_plane_router,
)
from pulse109.control_plane.router import BundleVerifierProvider
from pulse109.database import get_engine
from pulse109.datalab import PostgresDataLabService, create_datalab_router
from pulse109.decisions.publication import ConfidencePublicationService
from pulse109.decisions.publication_router import create_confidence_publication_router
from pulse109.discovery import (
    EmptyDiscoveryRepository,
    PostgresDiscoveryRepository,
    create_discovery_router,
)
from pulse109.incidents import (
    IncidentService,
    InMemoryIncidentRepository,
    PostgresIncidentRepository,
    PostgresIncidentService,
    create_incident_router,
)
from pulse109.incidents.workspace import PostgresIncidentWorkspaceService
from pulse109.incidents.workspace_advisors import (
    ManualPathOwnershipAdvisor,
    OutcomeMemoryAdvisor,
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
from pulse109.next_action import NextActionAdvisor, create_next_action_router
from pulse109.observability import configure_observability
from pulse109.operations import PostgresOperationsService, create_operations_router
from pulse109.outcome_memory import (
    OutcomeMemory,
    PostgresOutcomeMemoryReader,
    SyntheticOutcomeMemoryReader,
)
from pulse109.outcomes import (
    ClosureIntegrityService,
    PostgresClosureRepository,
    create_closure_router,
)
from pulse109.ownership.outcomes import HandoffOutcomeService
from pulse109.ownership.repository import EmptyOwnershipRepository, PostgresOwnershipRepository
from pulse109.ownership.router import create_ownership_router
from pulse109.ownership.service import OwnershipService
from pulse109.privacy import (
    InMemoryPrivateRefRepository,
    PostgresPrivateRefRepository,
    PrivacyService,
    create_privacy_router,
)
from pulse109.recurrence import (
    PostgresRecurrenceRepository,
    RecurrenceService,
    create_recurrence_router,
)
from pulse109.replay import (
    FileSnapshotStore,
    MemoryReplayRepository,
    PolicyMetrics,
    PostgresReplayRepository,
    ReplayReport,
    ReplayRepository,
    create_replay_router,
)
from pulse109.reports import ReportRuntime, create_report_router
from pulse109.retrieval import HybridRetriever, create_retrieval_router, synthetic_corpus
from pulse109.security import create_session_router

app = FastAPI(
    title="Pulse 109 Core API",
    version=__version__,
    docs_url="/docs"
    if get_settings().effective_profile in {"local", "development", "test", "demo"}
    else None,
    redoc_url=None,
)
configure_observability(app, get_settings())

# Memory is an explicit local/test fallback. Pilot and production always use PostgreSQL.
settings = get_settings()
use_postgres_manual_path = settings.effective_profile in {"demo", "pilot", "production"} or (
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
            allow_synthetic=settings.effective_profile in {"local", "development", "test", "demo"},
        )
    )
)
ownership_repository: PostgresOwnershipRepository | EmptyOwnershipRepository
handoff_service: HandoffOutcomeService | None
if use_postgres_manual_path:
    ownership_repository = PostgresOwnershipRepository(
        settings.database_url,
        allow_synthetic=settings.effective_profile in {"local", "development", "test", "demo"},
    )
    handoff_service = HandoffOutcomeService(ownership_repository)
else:
    ownership_repository = EmptyOwnershipRepository()
    handoff_service = None
ownership_service = OwnershipService(
    ownership_repository,
    allow_synthetic=settings.effective_profile in {"local", "development", "test", "demo"},
)
app.include_router(create_ownership_router(manual_service, ownership_service, handoff_service))
app.include_router(
    create_catalog_router(
        PolicyService(settings.database_url if use_postgres_manual_path else None)
    )
)
app.include_router(
    create_confidence_publication_router(
        ConfidencePublicationService(
            settings.database_url,
            allow_synthetic=settings.effective_profile in {"local", "development", "test", "demo"},
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
app.include_router(
    create_recurrence_router(
        RecurrenceService(PostgresRecurrenceRepository(settings.database_url))
        if use_postgres_manual_path
        else None
    )
)

synthetic_read_models = settings.effective_profile in {"local", "development", "test", "demo"}
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
# The war room is a read model over the services above. It owns no state and
# issues no commands, so every write still goes through its own domain endpoint.
next_action_advisor = NextActionAdvisor()
incident_workspace_service: PostgresIncidentWorkspaceService | None = None
if use_postgres_manual_path:
    # Outcome memory answers for the incident's leading appeal, which is where
    # its provenance chain starts. With no verified closures yet it abstains,
    # which the war room shows as such rather than as "not configured".
    incident_workspace_service = PostgresIncidentWorkspaceService(
        settings.database_url,
        detail_reader=incident_service,
        ownership=ManualPathOwnershipAdvisor(manual_service, ownership_service),
        # Production retrieval refuses to yield candidates until an approved
        # corpus exists, which is correct and leaves the capability invisible.
        # A profile that already declares its read models synthetic gets the
        # demo's own verified closures instead, each labelled as synthetic in
        # its own provenance.
        outcomes=OutcomeMemoryAdvisor(
            OutcomeMemory(
                reader=(
                    SyntheticOutcomeMemoryReader(settings.database_url)
                    if synthetic_read_models
                    else PostgresOutcomeMemoryReader(settings.database_url)
                )
            ),
            allow_synthetic=synthetic_read_models,
        ),
        next_actions=next_action_advisor,
        synthetic=synthetic_read_models,
    )
app.include_router(create_incident_router(incident_service, incident_workspace_service))
app.include_router(create_next_action_router(next_action_advisor, incident_workspace_service))

analytics_service = AnalyticsService(synthetic=synthetic_read_models)
alert_store: AlertStore
if use_postgres_manual_path:
    alert_store = PostgresAlertStore(settings.database_url)
else:
    alert_store = AlertStore()

if synthetic_read_models:
    # Seeding demo alerts is a convenience, never a startup requirement. In
    # postgres mode this is a real INSERT, and an unreachable database at
    # import time used to exit the process with code 1 instead of letting
    # /v1/health/ready report the real state. Degrade instead of dying.
    try:
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
    except Exception:
        logging.getLogger(__name__).warning(
            "demo alert seed skipped, storage unavailable at import", exc_info=True
        )
app.include_router(create_analytics_router(analytics_service, alert_store))

report_runtime = ReportRuntime(analytics_service)
app.include_router(create_report_router(report_runtime))

privacy_repository: InMemoryPrivateRefRepository | PostgresPrivateRefRepository
if use_postgres_manual_path:
    privacy_repository = PostgresPrivateRefRepository(settings.database_url)
else:
    privacy_repository = InMemoryPrivateRefRepository()
privacy_service = PrivacyService(privacy_repository)
app.include_router(create_privacy_router(privacy_service))
app.include_router(create_session_router())
app.include_router(
    create_datalab_router(
        PostgresDataLabService(settings.database_url, synthetic=synthetic_read_models)
        if use_postgres_manual_path
        else None
    )
)
app.include_router(
    create_operations_router(
        PostgresOperationsService(settings.database_url, synthetic=synthetic_read_models)
        if use_postgres_manual_path
        else None
    )
)
app.include_router(
    create_discovery_router(
        PostgresDiscoveryRepository(settings.database_url)
        if use_postgres_manual_path
        else EmptyDiscoveryRepository(),
        synthetic=synthetic_read_models,
        enabled=use_postgres_manual_path,
    )
)

replay_repository: ReplayRepository | None
if use_postgres_manual_path:
    snapshot_store = FileSnapshotStore(settings.replay_snapshot_dir)
    replay_repository = PostgresReplayRepository(settings.database_url, snapshot_store)
elif synthetic_read_models:
    mem_repo = MemoryReplayRepository()
    mem_repo.persist_report(
        ReplayReport(
            report_id="replay-rep-synthetic-001",
            dataset_id="dataset-kar-2026-q3",
            region_id="KAR",
            dataset_digest="a" * 64,
            baseline_policy_id="routing-kar-standard",
            baseline_version="1.0.0",
            candidate_policy_id="routing-kar-candidate",
            candidate_version="1.1.0",
            cutoff_at=datetime(2026, 9, 10, 23, 59, tzinfo=timezone.utc),
            baseline=PolicyMetrics(
                evaluated_count=120,
                synthetic_count=120,
                route_change_count=0,
                labeled_count=120,
                confirmed_route_agreement=0.82,
                route_matched_case_count=98,
                historical_handoff_rate_on_route_matched_cases=0.08,
                operator_override_rate=0.18,
                first_pass_acceptance_rate=0.82,
                language_slice_agreement={"kk": 0.80, "ru": 0.84, "mixed": 0.81},
            ),
            candidate=PolicyMetrics(
                evaluated_count=120,
                synthetic_count=120,
                route_change_count=14,
                labeled_count=120,
                confirmed_route_agreement=0.91,
                route_matched_case_count=109,
                historical_handoff_rate_on_route_matched_cases=0.03,
                operator_override_rate=0.09,
                first_pass_acceptance_rate=0.91,
                language_slice_agreement={"kk": 0.90, "ru": 0.92, "mixed": 0.89},
            ),
            decision=(
                "descriptive historical replay complete; candidate shows improved agreement "
                "and reduced handoffs across all language slices"
            ),
            promoted=False,
        )
    )
    replay_repository = mem_repo
else:
    replay_repository = None
app.include_router(create_replay_router(replay_repository, allow_synthetic=synthetic_read_models))


def _resolve_control_plane_verifier(s: Settings) -> BundleVerifierProvider | None:
    trusted_keys: dict[str, Ed25519PublicKey] = {}
    for entry in s.control_plane_trusted_keys:
        key_id, sep, path_or_key = entry.partition("=")
        if sep and key_id and path_or_key:
            p = Path(path_or_key)
            if p.is_file():
                loaded = serialization.load_pem_public_key(p.read_bytes())
                if isinstance(loaded, Ed25519PublicKey):
                    trusted_keys[key_id] = loaded
    if trusted_keys:
        return lambda reg: BundleVerifier(trusted_keys, expected_region_id=reg)
    if s.effective_profile in {"local", "development", "test", "demo"}:
        dev_key = Ed25519PrivateKey.generate().public_key()
        return lambda reg: BundleVerifier(
            {"synthetic-test-key": dev_key, "key-kar": dev_key},
            expected_region_id=reg,
        )
    return None


bundle_repository: BundleRepository
if use_postgres_manual_path:
    bundle_repository = PostgresBundleRepository(settings.database_url)
else:
    bundle_repository = MemoryBundleRepository()
app.include_router(
    create_control_plane_router(
        bundle_repository,
        verifier=_resolve_control_plane_verifier(settings),
    )
)


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
        return {
            "status": "ready",
            "profile": settings.effective_profile,
            "checks": {"database": "disabled-by-profile"},
        }

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

    return {
        "status": "ready",
        "profile": settings.effective_profile,
        "checks": {"database": "ready"},
    }
