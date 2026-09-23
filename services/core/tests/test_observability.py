import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pulse109.config import Settings
from pulse109.observability import JsonFormatter, configure_observability, log_safe


def app_with_correlation() -> FastAPI:
    app = FastAPI()

    @app.get("/probe")
    def probe() -> dict[str, str]:
        return {"status": "ok"}

    configure_observability(app, Settings(environment="test", otel_enabled=False))
    return app


def test_correlation_id_is_propagated_or_generated() -> None:
    with TestClient(app_with_correlation()) as client:
        supplied = client.get("/probe", headers={"X-Correlation-Id": "trace-safe-123"})
        generated = client.get("/probe")
    assert supplied.headers["X-Correlation-Id"] == "trace-safe-123"
    assert len(generated.headers["X-Correlation-Id"]) >= 8


def test_unsafe_correlation_id_is_rejected_without_echoing_it() -> None:
    with TestClient(app_with_correlation()) as client:
        response = client.get("/probe", headers={"X-Correlation-Id": "bad value"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_correlation_id"


def test_structured_logging_rejects_raw_or_unbounded_fields() -> None:
    logger = logging.getLogger("pulse109.test")
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.handlers = [handler]
    log_safe(logger, logging.INFO, "assignment queued", region_id="ALA", status="queued")
    with pytest.raises(ValueError, match="unsafe"):
        log_safe(logger, logging.INFO, "must not log body", appeal_text="private")
