"""Typed inference boundary; the core does not own model execution."""

from __future__ import annotations

from typing import Protocol

from pulse109_inference.engine import classify
from pulse109_inference.models import InferenceRequest, InferenceResponse


class InferenceProvider(Protocol):
    def classify(self, request: InferenceRequest) -> InferenceResponse: ...


class LocalLexicalInferenceProvider:
    """Explicit offline CPU fallback for local/test and replay workflows."""

    def classify(self, request: InferenceRequest) -> InferenceResponse:
        return classify(request)
