from fastapi import FastAPI

app = FastAPI(title="Pulse 109 Replay Adapter", version="0.1.0", docs_url=None, redoc_url=None)


@app.get("/v1/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "alive", "service": "adapter-runtime"}


@app.get("/v1/health/ready")
async def readiness() -> dict[str, str]:
    return {"status": "ready", "adapter": "replay", "external_system": "not-configured"}
