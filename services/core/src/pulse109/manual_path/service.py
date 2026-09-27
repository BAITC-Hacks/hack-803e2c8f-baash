"""Application operations for the ML-independent manual workflow."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from pulse109_inference.models import InferenceRequest

from pulse109.decisions import InferenceProvider, LocalLexicalInferenceProvider
from pulse109.security import (
    MockMalwareScanner,
    check_pdf_active_content,
    sanitize_filename,
    validate_attachment,
)

from .models import (
    Appeal,
    AppealDetail,
    AssignmentCommand,
    AttachmentRef,
    AttachmentUploadInput,
    ClassificationInput,
    ClassificationRecommendation,
    CreateRequest,
    DecisionReceipt,
    DeliverySyncStatus,
    LatestAssignment,
    OperatorDecision,
    RankedLabel,
    ServiceDefinition,
    StatusEventInput,
    SyncReceipt,
    SyncState,
    TimelineEvent,
)
from .repository import InMemoryManualRepository


class ManualPathError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


# integration.outbox keeps the worker's transport vocabulary, constrained by the
# CHECK in migration 0002. DeliverySyncStatus is what an operator sees on the
# appeal card. The projection between them has to be total: a partial one passed
# unmapped values straight to pydantic, so reading an appeal returned 500 as soon
# as the worker published its outbox entry.
OUTBOX_SYNC_STATUS: dict[str, DeliverySyncStatus] = {
    "pending": "queued",
    "processing": "queued",
    "published": "delivered",
    "retrying": "retrying",
    "dead_letter": "failed_permanent",
}


def sync_status_from_outbox(outbox_status: str) -> DeliverySyncStatus:
    """Project a stored outbox status onto the operator-facing vocabulary.

    Fails closed. An unmapped status means a storage state shipped without a
    matching entry here, and guessing which one it resembles would misreport
    delivery to the operator.
    """
    try:
        return OUTBOX_SYNC_STATUS[outbox_status]
    except KeyError as error:
        raise ManualPathError(
            "unknown_outbox_status", "Outbox synchronization state needs review.", 503
        ) from error


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, default=str, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _redact_text(value: str | None) -> str:
    if not value or not value.strip():
        return "[NO_TEXT]"
    redacted = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", value)
    redacted = re.sub(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)", "[PHONE_OR_ID]", redacted)
    return redacted.strip()


class ManualPathService:
    def __init__(
        self,
        repository: InMemoryManualRepository,
        inference_provider: InferenceProvider | None = None,
    ) -> None:
        self.repository = repository
        self.inference_provider = inference_provider or LocalLexicalInferenceProvider()

    def list_services(self, *, region_id: str, effective_at: datetime) -> list[ServiceDefinition]:
        del effective_at
        effective_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        definitions = (
            ("service:roads", "Жол қызметі", "Дорожная служба", ["topic:roads"]),
            ("service:utilities", "Коммуналдық қызмет", "Коммунальная служба", ["topic:utilities"]),
            ("service:sanitation", "Тазалық қызметі", "Служба санитарии", ["topic:waste"]),
        )
        return [
            ServiceDefinition(
                service_id=service_id,
                region_id=region_id,
                version="synthetic-1.0.0",
                effective_from=effective_from,
                display_name={"kk": kk, "ru": ru},
                topic_ids=topic_ids,
                required_fields=[],
                active=True,
            )
            for service_id, kk, ru, topic_ids in definitions
        ]

    @staticmethod
    def _scope(region_id: str, allowed_region: str) -> None:
        if region_id != allowed_region:
            raise ManualPathError(
                "region_scope_denied", "The request is outside the actor region scope.", 403
            )

    @staticmethod
    def _event(
        state: Any,
        appeal_id: UUID,
        event_type: str,
        actor: str,
        payload: dict[str, Any],
        occurred_at: datetime | None = None,
        occurred_at_quality: str | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": uuid4(),
            "event_type": event_type,
            "occurred_at": occurred_at,
            "occurred_at_quality": occurred_at_quality or ("exact" if occurred_at else "missing"),
            "observed_at": _now(),
            "actor_type": actor,
            "actor_id_token": actor,
            "payload": payload,
        }
        state.timelines.setdefault(appeal_id, []).append(event)
        return event

    @staticmethod
    def _audit(
        state: Any,
        action: str,
        appeal_id: UUID,
        region_id: str,
        actor: str,
        payload: dict[str, Any],
    ) -> UUID:
        event_id = uuid4()
        state.audit.append(
            {
                "event_id": event_id,
                "action": action,
                "aggregate_id": str(appeal_id),
                "region_id": region_id,
                "actor_id_token": actor,
                "observed_at": _now(),
                "payload": payload,
            }
        )
        return event_id

    @staticmethod
    def _outbox(
        state: Any, event_type: str, appeal_id: UUID, region_id: str, payload: dict[str, Any]
    ) -> UUID:
        event_id = uuid4()
        state.outbox.append(
            {
                "event_id": event_id,
                "event_type": event_type,
                "subject_id": str(appeal_id),
                "region_id": region_id,
                "status": "pending",
                "payload": payload,
                "created_at": _now(),
            }
        )
        return event_id

    def create(
        self,
        command: CreateRequest,
        *,
        idempotency_key: str,
        region_id: str,
        actor: str = "system",
        correlation_id: str | None = None,
    ) -> tuple[Appeal, bool]:
        del correlation_id
        self._scope(command.region_id, region_id)
        body = command.model_dump(mode="json")
        request_hash = _hash(body)
        key = ("create", idempotency_key)
        with self.repository.transaction() as state:
            prior = state.idempotency.get(key)
            if prior:
                if prior[0] != request_hash:
                    raise ManualPathError(
                        "idempotency_conflict", "The idempotency key has a different request body."
                    )
                return Appeal.model_validate(prior[1]), True
            source_key = (command.source_system, command.source_request_id)
            existing = state.source_index.get(source_key)
            if existing:
                current = Appeal.model_validate(state.appeals[existing])
                if state.source_hashes[source_key] != request_hash:
                    raise ManualPathError(
                        "source_identity_conflict",
                        "The source identity has a different request body.",
                    )
                state.idempotency[key] = (request_hash, current.model_dump(mode="json"))
                return current, True
            appeal = Appeal(request_id=uuid4(), created_at=_now(), version=1, status="new", **body)
            state.appeals[appeal.request_id] = appeal.model_dump(mode="json")
            state.source_index[source_key] = appeal.request_id
            state.source_hashes[source_key] = request_hash
            self._event(
                state,
                appeal.request_id,
                "appeal.created.v1",
                actor,
                {
                    "source_system": appeal.source_system,
                    "source_request_id": appeal.source_request_id,
                    "channel": appeal.channel,
                    "language": appeal.language,
                },
            )
            self._audit(
                state, "appeal.created", appeal.request_id, region_id, actor, {"status": "new"}
            )
            self._outbox(
                state,
                "appeal.created.v1",
                appeal.request_id,
                region_id,
                {
                    "source_system": appeal.source_system,
                    "source_request_id": appeal.source_request_id,
                },
            )
            state.idempotency[key] = (request_hash, appeal.model_dump(mode="json"))
            return appeal, False

    def _get(self, state: Any, request_id: UUID, region_id: str) -> Appeal:
        record = state.appeals.get(request_id)
        if not record:
            raise ManualPathError("not_found", "Appeal not found.", 404)
        appeal = Appeal.model_validate(record)
        self._scope(appeal.region_id, region_id)
        return appeal

    def detail(self, request_id: UUID, *, region_id: str) -> AppealDetail:
        state = self.repository.state
        appeal = self._get(state, request_id, region_id)
        timeline = [
            TimelineEvent.model_validate(event) for event in state.timelines.get(request_id, [])
        ]
        decision_record = state.decisions.get(request_id)
        decision = (
            OperatorDecision.model_validate(
                {name: decision_record.get(name) for name in OperatorDecision.model_fields}
            )
            if decision_record
            else None
        )
        sync = next(
            (item for item in reversed(state.outbox) if item["subject_id"] == str(request_id)), None
        )
        sync_receipt = None
        if sync:
            sync_receipt = SyncState(
                status=sync_status_from_outbox(str(sync["status"])),
            )
        return AppealDetail(
            **appeal.model_dump(),
            timeline=timeline,
            current_decision=decision,
            synchronization=sync_receipt,
        )

    def list_appeals(
        self,
        *,
        region_id: str,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Appeal]:
        state = self.repository.state
        matched = [
            Appeal.model_validate(appeal)
            for appeal in state.appeals.values()
            if (region_id == "ALL" or appeal.get("region_id") == region_id)
            and (status is None or appeal.get("status") == status)
        ]
        matched.sort(key=lambda a: a.created_at, reverse=True)
        return matched[offset : offset + limit]

    def upload_attachment(
        self,
        request_id: UUID,
        command: AttachmentUploadInput,
        *,
        region_id: str,
        actor: str,
    ) -> AttachmentRef:
        with self.repository.transaction() as state:
            self._get(state, request_id, region_id)
            try:
                content = base64.b64decode(command.content_base64)
            except Exception as exc:
                raise ManualPathError(
                    "invalid_attachment_encoding", "Base64 decoding failed.", 422
                ) from exc

            sanitized_name = sanitize_filename(command.file_name)
            validation = validate_attachment(content, command.mime_type)
            if not validation.is_valid:
                raise ManualPathError(
                    validation.error_code or "invalid_attachment",
                    validation.error_message or "Attachment validation failed.",
                    422,
                )

            if validation.detected_mime == "application/pdf":
                pdf_err = check_pdf_active_content(content)
                if pdf_err:
                    raise ManualPathError(pdf_err, "PDF contains active scripts or actions.", 422)

            scanner = MockMalwareScanner()
            scan_res = scanner.scan(content, validation.sha256)
            if not scan_res.is_clean:
                raise ManualPathError("malware_detected", "Malware detected in attachment.", 422)

            attachment_id = uuid4()
            now = datetime.now(timezone.utc)
            object_ref = f"attachment://{validation.sha256}/{sanitized_name}"
            record = {
                "attachment_id": attachment_id,
                "appeal_id": request_id,
                "object_ref": object_ref,
                "file_name": sanitized_name,
                "mime_type": validation.detected_mime or command.mime_type,
                "byte_size": validation.byte_size,
                "object_hash": validation.sha256,
                "data_classification": "internal",
                "created_at": now,
            }
            state.attachments.setdefault(request_id, []).append(record)
            self._audit(
                state,
                "attachment.uploaded",
                request_id,
                region_id,
                actor,
                {
                    "attachment_id": str(attachment_id),
                    "file_name": sanitized_name,
                    "object_hash": validation.sha256,
                    "data_classification": "internal",
                },
            )
            return AttachmentRef.model_validate(record)

    def list_attachments(self, request_id: UUID, *, region_id: str) -> list[AttachmentRef]:
        state = self.repository.state
        self._get(state, request_id, region_id)
        records = state.attachments.get(request_id, [])
        return [AttachmentRef.model_validate(r) for r in records]

    def classify(
        self,
        request_id: UUID,
        command: ClassificationInput,
        *,
        idempotency_key: str,
        region_id: str,
        correlation_id: str,
    ) -> ClassificationRecommendation:
        with self.repository.transaction() as state:
            appeal = self._get(state, request_id, region_id)
            key = (f"classification:{request_id}", idempotency_key)
            request_hash = _hash(command.model_dump(mode="json"))
            if key in state.idempotency:
                prior_hash, prior_response = state.idempotency[key]
                if prior_hash != request_hash:
                    raise ManualPathError(
                        "idempotency_conflict", "The idempotency key has a different request body."
                    )
                return ClassificationRecommendation.model_validate(prior_response)
            if appeal.version != command.request_version:
                raise ManualPathError(
                    "stale_version", "The appeal changed since classification was requested."
                )
            if command.force_model_alias is not None:
                raise ManualPathError(
                    "model_alias_unavailable",
                    "The requested production model alias is not available in this profile.",
                    503,
                )

            snapshot_id = uuid5(NAMESPACE_URL, f"pulse109:{request_id}:{appeal.version}")
            response = self.inference_provider.classify(
                InferenceRequest(
                    contract_version="1.0.0",
                    task="routing",
                    request_id=request_id,
                    request_version=appeal.version,
                    region_id=appeal.region_id,
                    feature_snapshot_id=snapshot_id,
                    input_contract_version="canonical_request/1.0.0",
                    preprocess_version="basic-pii-redaction/1.0.0",
                    taxonomy_version="temporary/1.0.0",
                    model_alias="baseline",
                    redacted_text=_redact_text(appeal.text),
                    language=appeal.language,
                    channel=appeal.channel,
                    correlation_id=correlation_id,
                    trace_id=correlation_id,
                    requested_at=_now(),
                )
            )
            recommendation = ClassificationRecommendation(
                recommendation_id=response.recommendation_id,
                request_id=response.request_id,
                request_version=response.request_version,
                model_version=response.model_version,
                taxonomy_version=response.taxonomy_version,
                top_topics=[
                    RankedLabel(id=item.id, score=item.score) for item in response.top_topics
                ],
                top_services=[
                    RankedLabel(id=item.id, score=item.score) for item in response.top_services
                ],
                priority=response.priority,
                confidence_band=response.confidence_band,
                out_of_domain_score=response.ood_score,
                rule_hits=list(response.rule_hits),
                missing_fields=["text"] if appeal.text is None else [],
                explanation=[
                    "Deterministic lexical CPU fallback; no production quality claim.",
                    "A human must confirm or correct this recommendation.",
                ],
                produced_at=response.produced_at,
            )
            stored = recommendation.model_dump(mode="json")
            state.recommendations[recommendation.recommendation_id] = stored
            state.idempotency[key] = (request_hash, stored)
            self._audit(
                state,
                "ai.recommendation.produced",
                request_id,
                region_id,
                "system",
                {
                    "recommendation_id": str(recommendation.recommendation_id),
                    "model_version": recommendation.model_version,
                    "requires_human_confirmation": True,
                },
            )
            return recommendation

    def decide(
        self,
        request_id: UUID,
        command: OperatorDecision,
        *,
        idempotency_key: str,
        region_id: str,
        actor: str,
    ) -> DecisionReceipt:
        with self.repository.transaction() as state:
            appeal = self._get(state, request_id, region_id)
            key = (f"decision:{request_id}", idempotency_key)
            request_hash = _hash(command.model_dump(mode="json"))
            if key in state.idempotency:
                prior_hash, prior_response = state.idempotency[key]
                if prior_hash != request_hash:
                    raise ManualPathError(
                        "idempotency_conflict", "The idempotency key has a different request body."
                    )
                return DecisionReceipt.model_validate(prior_response)
            if appeal.version != command.request_version:
                raise ManualPathError(
                    "stale_version", "The appeal changed since the operator opened it."
                )
            if command.action == "corrected" and not command.correction_reason:
                raise ManualPathError(
                    "correction_reason_required", "A correction reason is required.", 422
                )
            if command.action in {"accepted", "corrected"} and command.recommendation_id is None:
                raise ManualPathError(
                    "recommendation_required",
                    "Accepted and corrected decisions require a recommendation.",
                    422,
                )
            decision_id, audit_id = uuid4(), uuid4()
            new_version = appeal.version + 1
            record = {
                "decision_id": decision_id,
                "request_id": request_id,
                "request_version": command.request_version,
                "new_version": new_version,
                "recommendation_id": command.recommendation_id,
                "topic_id": command.topic_id,
                "service_id": command.service_id,
                "priority": command.priority,
                "action": command.action,
                "correction_reason": command.correction_reason,
                "operator_note": command.operator_note,
                "actor_id_token": actor,
                "decided_at": _now(),
            }
            state.decisions[request_id] = record
            appeal.status, appeal.version = "triage", new_version
            state.appeals[request_id] = appeal.model_dump(mode="json")
            payload = {
                "topic_id": command.topic_id,
                "service_id": command.service_id,
                "priority": command.priority,
                "action": command.action,
                "recommendation_id": str(command.recommendation_id)
                if command.recommendation_id
                else None,
                "correction_reason": command.correction_reason,
            }
            self._event(state, request_id, "appeal.decision.recorded.v1", "operator", payload)
            state.audit.append(
                {
                    "event_id": audit_id,
                    "action": "appeal.decision.recorded",
                    "aggregate_id": str(request_id),
                    "region_id": region_id,
                    "actor_id_token": actor,
                    "observed_at": _now(),
                    "payload": payload,
                }
            )
            self._outbox(state, "appeal.decision.recorded.v1", request_id, region_id, payload)
            if command.recommendation_id:
                state.feedback.append(
                    {
                        "task": "routing",
                        "proposal_id": str(command.recommendation_id),
                        "human_action": command.action,
                        "reason_code": command.correction_reason,
                        "final_topic_id": command.topic_id,
                        "final_service_id": command.service_id,
                        "actor_id_token": actor,
                        "request_id": str(request_id),
                    }
                )
                self._outbox(
                    state, "ai.feedback.recorded.v1", request_id, region_id, state.feedback[-1]
                )
            receipt = DecisionReceipt(
                decision_id=decision_id,
                request_id=request_id,
                new_version=new_version,
                audit_event_id=audit_id,
            )
            state.idempotency[key] = (request_hash, receipt.model_dump(mode="json"))
            return receipt

    def status(
        self,
        request_id: UUID,
        command: StatusEventInput,
        *,
        idempotency_key: str,
        region_id: str,
        actor: str,
    ) -> TimelineEvent:
        with self.repository.transaction() as state:
            appeal = self._get(state, request_id, region_id)
            key = (f"status:{request_id}", idempotency_key)
            request_hash = _hash(command.model_dump(mode="json"))
            if key in state.idempotency:
                prior_hash, prior_response = state.idempotency[key]
                if prior_hash != request_hash:
                    raise ManualPathError(
                        "idempotency_conflict", "The idempotency key has a different request body."
                    )
                return TimelineEvent.model_validate(prior_response)
            duplicate = next(
                (
                    item
                    for item in state.timelines.get(request_id, [])
                    if item["payload"].get("source_event_id") == command.source_event_id
                ),
                None,
            )
            if duplicate:
                response = TimelineEvent.model_validate(duplicate)
                state.idempotency[key] = (request_hash, response.model_dump(mode="json"))
                return response
            if command.status in {"accepted", "waiting"}:
                raise ManualPathError(
                    "status_contract_gap",
                    "accepted and waiting require the canonical appeal status "
                    "contract to be widened.",
                    422,
                )
            previous_status = appeal.status
            appeal.status, appeal.version = command.status, appeal.version + 1
            state.appeals[request_id] = appeal.model_dump(mode="json")
            payload = {
                "previous_status": previous_status,
                "new_status": command.status,
                "source_event_id": command.source_event_id,
                "source_system": command.source_system,
                "source_timezone": command.source_timezone,
                "reason_code": command.reason_code,
                "evidence_refs": command.evidence_refs,
            }
            event = self._event(
                state,
                request_id,
                "appeal.status.changed.v1",
                actor,
                payload,
                command.occurred_at,
                command.occurred_at_quality,
            )
            self._audit(state, "appeal.status.changed", request_id, region_id, actor, payload)
            self._outbox(state, "appeal.status.changed.v1", request_id, region_id, payload)
            response = TimelineEvent.model_validate(event)
            state.idempotency[key] = (request_hash, response.model_dump(mode="json"))
            return response

    def assign(
        self,
        request_id: UUID,
        command: AssignmentCommand,
        *,
        idempotency_key: str,
        region_id: str,
        actor: str,
        override_authorized: bool = False,
    ) -> SyncReceipt:
        with self.repository.transaction() as state:
            appeal = self._get(state, request_id, region_id)
            key = (f"assignment:{request_id}", idempotency_key)
            request_hash = _hash(command.model_dump(mode="json"))
            if key in state.idempotency:
                prior_hash, prior_response = state.idempotency[key]
                if prior_hash != request_hash:
                    raise ManualPathError(
                        "idempotency_conflict", "The idempotency key has a different request body."
                    )
                return SyncReceipt.model_validate(prior_response)
            if appeal.version != command.request_version:
                raise ManualPathError(
                    "stale_version", "The appeal changed since the operator opened it."
                )
            if command.handoff_override_reason_code is not None:
                if not override_authorized:
                    raise ManualPathError(
                        "handoff_override_forbidden",
                        "A supervisor or administrator must authorize the handoff override.",
                        403,
                    )
                raise ManualPathError(
                    "handoff_override_not_required",
                    "No prior rejection supports a handoff override for this assignee.",
                    409,
                )
            appeal.status, appeal.version = "assigned", appeal.version + 1
            state.appeals[request_id] = appeal.model_dump(mode="json")
            payload = {
                "service_id": command.service_id,
                "assignee_unit_id": command.assignee_unit_id,
                "reason_code": command.reason_code,
                "policy_version": command.policy_version,
                "due_at": command.expected_due_at.isoformat() if command.expected_due_at else None,
            }
            self._event(state, request_id, "appeal.assigned.v1", actor, payload)
            self._audit(state, "appeal.assigned", request_id, region_id, actor, payload)
            outbox_id = self._outbox(state, "appeal.assigned.v1", request_id, region_id, payload)
            state.assignments.setdefault(request_id, []).append(
                LatestAssignment(
                    assignment_id=uuid4(),
                    request_id=request_id,
                    request_version=command.request_version,
                    new_version=appeal.version,
                    service_id=command.service_id,
                    assignee_unit_id=command.assignee_unit_id,
                    assigned_at=_now(),
                ).model_dump(mode="json")
            )
            receipt = SyncReceipt(outbox_event_id=outbox_id, status="queued")
            state.idempotency[key] = (request_hash, receipt.model_dump(mode="json"))
            return receipt

    def latest_assignment(self, request_id: UUID, *, region_id: str) -> LatestAssignment:
        state = self.repository.state
        self._get(state, request_id, region_id)
        assignments = state.assignments.get(request_id, [])
        if not assignments:
            raise ManualPathError("assignment_not_found", "No assignment is recorded.", 404)
        return LatestAssignment.model_validate(assignments[-1])
