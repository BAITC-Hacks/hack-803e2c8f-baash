"""Minimal Open311 v2-compatible synthetic HTTP surface."""

from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request
from pulse109.config import Settings
from pulse109.observability import configure_observability

from .adapter import Open311SyntheticAdapter

app = FastAPI(title="Pulse 109 Open311 compatibility sandbox", docs_url=None, redoc_url=None)
configure_observability(app, Settings(service_name="adapter-open311-synthetic"))
adapter = Open311SyntheticAdapter()


@app.get("/v2/services.json")
def services() -> list[dict[str, object]]:
    return adapter.fetch_catalog()


@app.post("/v2/requests.json")
async def create_request(request: Request) -> list[dict[str, object]]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
    else:
        form = parse_qs((await request.body()).decode("utf-8"), keep_blank_values=True)
        payload = {key: values[-1] for key, values in form.items()}
    command_id = request.headers.get("idempotency-key")
    if not command_id:
        raise HTTPException(status_code=400, detail="Idempotency-Key is required")
    result = adapter.create_or_import(command_id, payload)
    return [{"service_request_id": result.external_id}]


@app.get("/v2/requests/{service_request_id}.json")
def get_request(service_request_id: str) -> list[dict[str, object]]:
    record = adapter.requests.get(service_request_id)
    if record is None:
        raise HTTPException(status_code=404, detail="service request not found")
    return [record]


@app.get("/v1/health/live")
def live() -> dict[str, object]:
    return {"status": "alive", "adapter": adapter.adapter_id, "synthetic_only": True}
