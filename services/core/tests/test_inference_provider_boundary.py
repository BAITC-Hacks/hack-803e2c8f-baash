"""Core classification reaches inference only through the injected provider."""

from uuid import uuid4

from pulse109.decisions import LocalLexicalInferenceProvider
from pulse109.manual_path.models import ClassificationInput, CreateRequest
from pulse109.manual_path.repository import InMemoryManualRepository
from pulse109.manual_path.service import ManualPathService
from pulse109_inference.models import InferenceRequest, InferenceResponse


class RecordingProvider:
    def __init__(self) -> None:
        self.calls: list[InferenceRequest] = []
        self.fallback = LocalLexicalInferenceProvider()

    def classify(self, request: InferenceRequest) -> InferenceResponse:
        self.calls.append(request)
        return self.fallback.classify(request)


def test_local_manual_classification_uses_injected_provider_once() -> None:
    provider = RecordingProvider()
    service = ManualPathService(InMemoryManualRepository(), inference_provider=provider)
    nonce = uuid4().hex
    appeal, _ = service.create(
        CreateRequest(
            source_system="synthetic-provider-test",
            source_request_id=nonce,
            region_id="ALA",
            received_at=None,
            received_at_quality="missing",
            channel="web",
            text="Synthetic water request without personal data.",
        ),
        idempotency_key=f"create-{nonce}",
        region_id="ALA",
    )

    first = service.classify(
        appeal.request_id,
        ClassificationInput(request_version=1),
        idempotency_key=f"classify-{nonce}",
        region_id="ALA",
        correlation_id=f"correlation-{nonce}",
    )
    replay = service.classify(
        appeal.request_id,
        ClassificationInput(request_version=1),
        idempotency_key=f"classify-{nonce}",
        region_id="ALA",
        correlation_id=f"correlation-{nonce}",
    )

    assert len(provider.calls) == 1
    assert provider.calls[0].region_id == "ALA"
    assert first.recommendation_id == replay.recommendation_id
    assert first.requires_human_confirmation is True
