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
    with pytest.raises(ValueError, match="unsafe"):
        log_safe(logger, logging.INFO, "must not log phone", phone="+77001234567")
    with pytest.raises(ValueError, match="unsafe"):
        log_safe(logger, logging.INFO, "must not log citizen", citizen_name="John Doe")
    with pytest.raises(ValueError, match="unsafe"):
        log_safe(logger, logging.INFO, "must not log address", address="Abay Ave 10")


def test_json_formatter_never_serializes_unauthorized_fields() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="safe status update",
        args=(),
        exc_info=None,
    )
    # Even if someone bypassed log_safe and set safe_fields containing unsafe fields
    record.safe_fields = {  # type: ignore[attr-defined]
        "region_id": "ALA",
        "raw_text": "leak candidate",
        "phone": "+77019998877",
    }
    formatted = formatter.format(record)
    assert "region_id" in formatted
    assert "leak candidate" not in formatted
    assert "+77019998877" not in formatted
    assert "phone" not in formatted
