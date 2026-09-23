from fastapi import FastAPI
from pulse109.config import Settings
from pulse109.observability import configure_observability

from .engine import classify
from .models import InferenceRequest, InferenceResponse

app = FastAPI(title="Pulse 109 Inference", version="0.1.0", docs_url=None, redoc_url=None)
configure_observability(app, Settings(service_name="ml-inference"))


@app.get("/v1/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "alive", "service": "ml-inference"}


@app.get("/v1/health/ready")
async def readiness() -> dict[str, str]:
    return {"status": "ready", "mode": "no-model-loaded"}


@app.post("/v1/inference/classify", response_model=InferenceResponse)
async def classify_request(request: InferenceRequest) -> InferenceResponse:
    return classify(request)
