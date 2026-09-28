from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from pulse109.config import Settings
from pulse109.observability import configure_observability
from starlette.responses import Response

from .analytics_intent import AnalyticsIntentRequest, AnalyticsIntentResponse, analytics_intent
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


@app.post("/v1/inference/analytics-intent", response_model=AnalyticsIntentResponse)
async def analytics_intent_request(request: AnalyticsIntentRequest) -> AnalyticsIntentResponse:
    return await analytics_intent(request)


@app.exception_handler(RequestValidationError)
async def safe_analytics_validation(request: Request, error: RequestValidationError) -> Response:
    if request.url.path != "/v1/inference/analytics-intent":
        return await request_validation_exception_handler(request, error)
    # FastAPI normally echoes invalid field values. A question may itself
    # contain PII; never return it or copy it into a diagnostic envelope.
    from starlette.responses import JSONResponse

    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "invalid_analytics_intent_request",
                "errors": [
                    {"location": list(item["loc"]), "type": item["type"]} for item in error.errors()
                ],
            }
        },
    )
