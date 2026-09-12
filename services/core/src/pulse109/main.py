from typing import Any

from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text

from pulse109 import __version__
from pulse109.config import get_settings
from pulse109.database import get_engine
from pulse109.manual_path import InMemoryManualRepository, ManualPathService, create_manual_router

app = FastAPI(
    title="Pulse 109 Core API",
    version=__version__,
    docs_url="/docs" if get_settings().environment in {"local", "development", "test"} else None,
    redoc_url=None,
)

# The synthetic/manual profile remains usable while PostgreSQL and ML are unavailable.
manual_repository = InMemoryManualRepository()
app.include_router(create_manual_router(ManualPathService(manual_repository)))


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
