from fastapi import FastAPI, HTTPException
from pulse109_adapter import AssignmentCommand
from pulse109_adapter.protocol import AdapterError

from pulse109_replay.store import ReplayStore

app = FastAPI(title="Pulse 109 Replay Adapter", version="0.1.0", docs_url=None, redoc_url=None)
store = ReplayStore()


@app.get("/v1/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "alive", "service": "adapter-runtime"}


@app.get("/v1/health/ready")
async def readiness() -> dict[str, str]:
    return {"status": "ready", "adapter": "replay", "external_system": "not-configured"}


@app.post("/v1/assignments")
async def assign(payload: dict[str, object]) -> dict[str, object]:
    try:
        result = store.assign(
            AssignmentCommand(
                command_id=str(payload["command_id"]),
                request_id=str(payload["request_id"]),
                source_system=str(payload.get("source_system", "replay")),
                region_id=str(payload["region_id"]),
                service_id=str(payload["service_id"]),
                assignee_unit_id=(
                    str(payload["assignee_unit_id"])
                    if payload.get("assignee_unit_id") is not None
                    else None
                ),
                reason_code=str(payload.get("reason_code", "adapter_delivery")),
            )
        )
    except (KeyError, AdapterError) as error:
        code = error.code if isinstance(error, AdapterError) else "invalid_command"
        raise HTTPException(
            status_code=503 if isinstance(error, AdapterError) and error.retryable else 422,
            detail={"code": code, "message": str(error)},
        ) from error
    return {
        "command_id": result.command_id,
        "confirmed": result.confirmed,
        "external_id": result.external_id,
        "response_code": result.response_code,
        "source_code": result.source_code,
    }
