"""Idempotent report job boundary, independent from rendering infrastructure."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from .models import ReportJob, ReportRequest


class ReportIdempotencyConflict(ValueError):
    pass


class ReportJobStore:
    def __init__(self) -> None:
        self._keys: dict[tuple[str, str], tuple[str, UUID]] = {}
        self.jobs: dict[UUID, ReportJob] = {}

    @staticmethod
    def request_hash(request: ReportRequest) -> str:
        encoded = json.dumps(request.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def enqueue(self, request: ReportRequest, *, idempotency_key: str) -> ReportJob:
        request_hash = self.request_hash(request)
        scope = (request.actor_token, idempotency_key)
        existing = self._keys.get(scope)
        if existing:
            if existing[0] != request_hash:
                raise ReportIdempotencyConflict("idempotency key reused with different request")
            return self.jobs[existing[1]]
        job = ReportJob(
            job_id=uuid4(),
            request_hash=request_hash,
            status="queued",
            created_at=datetime.now(timezone.utc),
        )
        self._keys[scope] = (request_hash, job.job_id)
        self.jobs[job.job_id] = job
        return job
