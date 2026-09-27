"""PostgreSQL-backed M2 manual path.

The local profile keeps the small in-memory implementation available for fast
tests.  This module is the production repository/application path: every
command owns one database transaction and writes the current projection,
append-only event, audit row, idempotency receipt, and outbox event together.
"""

from __future__ import annotations

import base64
import json
import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, cast
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import psycopg
from psycopg.rows import dict_row
from pulse109_inference.models import InferenceRequest

from pulse109.config import get_settings
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
    LatestAssignment,
    OperatorDecision,
    RankedLabel,
    ServiceDefinition,
    StatusEventInput,
    SyncReceipt,
    SyncState,
    TimelineEvent,
)
from .service import ManualPathError, _hash, sync_status_from_outbox


def _psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _redact_text(value: str | None) -> str:
    if not value or not value.strip():
        return "[NO_TEXT]"
    redacted = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", value)
    redacted = re.sub(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)", "[PHONE_OR_ID]", redacted)
    return redacted.strip()


class PostgresManualRepository:
    """Intent-level PostgreSQL repository for the manual critical path."""

    schema_hash = sha256(b"pulse109-manual-path-source-schema/1.0.0").hexdigest()
    schema_version = "manual-path/1.0.0"
    mapping_version = "manual-path/1.0.0"

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(_psycopg_url(self.database_url), row_factory=dict_row) as connection:
            yield connection

    def get_appeal_region(self, request_id: UUID) -> str | None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT region_id FROM appeals.appeal WHERE request_id = %s", (request_id,)
            )
            row = cursor.fetchone()
            return str(row["region_id"]) if row else None


class PostgresManualPathService:
    """M2 application service backed by PostgreSQL transactions."""

    def __init__(
        self,
        repository: PostgresManualRepository,
        inference_provider: InferenceProvider | None = None,
    ) -> None:
        self.repository = repository
        self.inference_provider = inference_provider or LocalLexicalInferenceProvider()

    @staticmethod
    def _scope(actual: str, requested: str) -> None:
        if actual != requested:
            raise ManualPathError(
                "region_scope_denied", "The request is outside the actor region scope.", 403
            )

    @staticmethod
    def _json(value: object) -> str:
        return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _load_json(value: Any, default: Any) -> Any:
        if value is None:
            return default
        if isinstance(value, str):
            return json.loads(value)
        return value

    def _idempotency(
        self, cursor: Any, scope: str, key: str, request_hash: str
    ) -> dict[str, Any] | None:
        # A missing row cannot be locked with FOR UPDATE. Serialize contenders
        # for this receipt until the enclosing command transaction commits.
        cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (f"{scope}:{key}",),
        )
        cursor.execute(
            """
            SELECT request_hash, response_body
            FROM integration.idempotency_key
            WHERE scope = %s AND idempotency_key = %s
            FOR UPDATE
            """,
            (scope, key),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        if row["request_hash"] != request_hash:
            raise ManualPathError(
                "idempotency_conflict", "The idempotency key has a different request body."
            )
        return cast(dict[str, Any], self._load_json(row["response_body"], {}))

    def _save_idempotency(
        self,
        cursor: Any,
        scope: str,
        key: str,
        request_hash: str,
        response: dict[str, Any],
        *,
        resource_id: UUID | None = None,
        response_status: int = 200,
    ) -> None:
        cursor.execute(
            """
            INSERT INTO integration.idempotency_key
                (scope, idempotency_key, request_hash, resource_id, response_status, response_body)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            """,
            (scope, key, request_hash, resource_id, response_status, self._json(response)),
        )

    def _source_system(self, cursor: Any, command: CreateRequest) -> UUID:
        cursor.execute(
            """
            INSERT INTO integration.source_system
                (system_code, display_name, region_id, adapter_id, adapter_version)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (system_code) DO UPDATE SET updated_at = now()
            RETURNING id, region_id
            """,
            (
                command.source_system,
                f"{command.source_system} manual intake",
                command.region_id,
                "manual-intake",
                self.repository.schema_version,
            ),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("source system upsert returned no id")
        if row["region_id"] != command.region_id:
            raise ManualPathError(
                "source_system_region_conflict",
                "The source system is registered to a different region.",
            )
        return cast(UUID, row["id"])

    def _source_schema(self, cursor: Any, source_system_id: UUID, observed_at: datetime) -> UUID:
        cursor.execute(
            """
            INSERT INTO integration.source_schema_version
                (source_system_id, version, contract_version, mapping_version,
                 schema_hash, status, effective_from)
            VALUES (%s, %s, %s, %s, %s, 'approved', %s)
            ON CONFLICT (source_system_id, version) DO NOTHING
            RETURNING id
            """,
            (
                source_system_id,
                self.repository.schema_version,
                "canonical_request/1.0.0",
                self.repository.mapping_version,
                self.repository.schema_hash,
                observed_at,
            ),
        )
        row = cursor.fetchone()
        if row is not None:
            return cast(UUID, row["id"])
        cursor.execute(
            """
            SELECT id, schema_hash, mapping_version
            FROM integration.source_schema_version
            WHERE source_system_id = %s AND version = %s
            """,
            (source_system_id, self.repository.schema_version),
        )
        row = cursor.fetchone()
        if (
            row is None
            or row["schema_hash"].lower() != self.repository.schema_hash
            or row["mapping_version"] != self.repository.mapping_version
        ):
            raise ManualPathError(
                "source_schema_conflict", "The manual source schema is not approved."
            )
        return cast(UUID, row["id"])

    def _appeal_from_row(self, row: dict[str, Any]) -> Appeal:
        location = None
        if any(
            row.get(name) is not None
            for name in ("geo_id", "object_id", "latitude", "longitude", "precision_m")
        ):
            from .models import LocationInput

            location = LocationInput(
                address_text_private_ref=row.get("address_private_ref"),
                geo_id=row.get("geo_id"),
                object_id=row.get("object_id"),
                latitude=row.get("latitude"),
                longitude=row.get("longitude"),
                precision_m=row.get("precision_m"),
            )
        return Appeal(
            request_id=row["request_id"],
            created_at=row["created_at"],
            version=row["version"],
            status=row["status"],
            source_system=row["source_system"],
            source_request_id=row["source_request_id"],
            region_id=row["region_id"],
            channel=row["channel"],
            language=row["language"],
            received_at=row["received_at"],
            received_at_quality=row["received_at_quality"],
            source_timezone=row["source_timezone"],
            text=row.get("redacted_text"),
            transcript_ref=row.get("transcript_ref"),
            media_refs=self._load_json(row.get("media_refs"), []),
            location=location,
            citizen_token=row.get("citizen_token"),
            source_payload_ref=row.get("raw_payload_ref"),
            consent_or_legal_basis=row.get("legal_basis"),
        )

    def _appeal(self, cursor: Any, request_id: UUID, *, lock: bool = False) -> Appeal:
        query = """
            SELECT a.*, ss.system_code AS source_system, sr.raw_payload_ref,
                   ac.redacted_text, ST_Y(a.location::geometry) AS latitude,
                   ST_X(a.location::geometry) AS longitude
            FROM appeals.appeal AS a
            JOIN integration.source_system AS ss ON ss.id = a.source_system_id
            JOIN integration.source_record AS sr ON sr.id = a.source_record_id
            LEFT JOIN privacy.appeal_content AS ac ON ac.appeal_id = a.request_id
            WHERE a.request_id = %s
            """
        if lock:
            query += " FOR UPDATE OF a"
        cursor.execute(query, (request_id,))
        row = cursor.fetchone()
        if row is None:
            raise ManualPathError("not_found", "Appeal not found.", 404)
        return self._appeal_from_row(row)

    def list_appeals(
        self,
        *,
        region_id: str,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Appeal]:
        with self.repository.connection() as connection, connection.cursor() as cursor:
            query = """
                SELECT a.*, ss.system_code AS source_system, sr.raw_payload_ref,
                       ac.redacted_text, ST_Y(a.location::geometry) AS latitude,
                       ST_X(a.location::geometry) AS longitude
                FROM appeals.appeal AS a
                JOIN integration.source_system AS ss ON ss.id = a.source_system_id
                JOIN integration.source_record AS sr ON sr.id = a.source_record_id
                LEFT JOIN privacy.appeal_content AS ac ON ac.appeal_id = a.request_id
                WHERE (a.region_id = %s OR %s = 'ALL')
            """
            params: list[Any] = [region_id, region_id]
            if status is not None:
                query += " AND a.status = %s"
                params.append(status)
            query += " ORDER BY a.observed_at DESC, a.request_id DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            cursor.execute(query, tuple(params))
            return [self._appeal_from_row(row) for row in cursor.fetchall()]

    def upload_attachment(
        self,
        request_id: UUID,
        command: AttachmentUploadInput,
        *,
        region_id: str,
        actor: str,
    ) -> AttachmentRef:
        settings = get_settings()
        if settings.effective_profile in {"pilot", "production"}:
            raise ManualPathError(
                "attachment_storage_unavailable",
                "Approved immutable storage and malware scanning are not configured.",
                503,
            )
        with self.repository.connection() as connection, connection.cursor() as cursor:
            appeal = self._appeal(cursor, request_id, lock=True)
            self._scope(appeal.region_id, region_id)

            try:
                content = base64.b64decode(command.content_base64, validate=True)
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
            at = _now()
            storage_dir = Path(settings.demo_attachment_dir)
            storage_dir.mkdir(parents=True, exist_ok=True)
            blob = storage_dir / validation.sha256
            try:
                with blob.open("xb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError:
                if sha256(blob.read_bytes()).hexdigest() != validation.sha256:
                    raise ManualPathError(
                        "attachment_hash_conflict", "Stored attachment hash mismatch.", 503
                    ) from None
            object_ref = f"demo-blob://sha256/{validation.sha256}/{sanitized_name}"
            cursor.execute(
                """
                INSERT INTO appeals.attachment_ref
                    (id, appeal_id, object_ref, object_hash, media_type,
                     byte_size, data_classification, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (appeal_id, object_hash) DO UPDATE SET
                    media_type = EXCLUDED.media_type
                RETURNING id, appeal_id, object_ref, object_hash, media_type,
                          byte_size, data_classification, created_at
                """,
                (
                    attachment_id,
                    request_id,
                    object_ref,
                    validation.sha256,
                    validation.detected_mime or command.mime_type,
                    validation.byte_size,
                    "internal",
                    at,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise ManualPathError("attachment_save_failed", "Failed to store attachment.", 500)

            self._audit(
                cursor,
                action="attachment.uploaded",
                aggregate_id=appeal.request_id,
                region_id=appeal.region_id,
                actor_type="user",
                actor_token=actor,
                correlation_id=str(request_id),
                payload={
                    "attachment_id": str(row["id"]),
                    "file_name": sanitized_name,
                    "object_hash": str(row["object_hash"]).strip(),
                    "data_classification": str(row["data_classification"]),
                },
            )
            return AttachmentRef(
                attachment_id=row["id"],
                appeal_id=row["appeal_id"],
                object_ref=str(row["object_ref"]),
                file_name=sanitized_name,
                mime_type=str(row["media_type"] or command.mime_type),
                byte_size=int(row["byte_size"] or 0),
                object_hash=str(row["object_hash"]).strip(),
                data_classification=row["data_classification"],
                created_at=row["created_at"],
            )

    def list_attachments(self, request_id: UUID, *, region_id: str) -> list[AttachmentRef]:
        with self.repository.connection() as connection, connection.cursor() as cursor:
            appeal = self._appeal(cursor, request_id, lock=False)
            self._scope(appeal.region_id, region_id)
            cursor.execute(
                """
                SELECT id, appeal_id, object_ref, object_hash, media_type,
                       byte_size, data_classification, created_at
                FROM appeals.attachment_ref
                WHERE appeal_id = %s
                ORDER BY created_at ASC
                """,
                (request_id,),
            )
            result: list[AttachmentRef] = []
            for row in cursor.fetchall():
                obj_ref = str(row["object_ref"])
                fname = obj_ref.split("/")[-1] if "/" in obj_ref else obj_ref
                result.append(
                    AttachmentRef(
                        attachment_id=row["id"],
                        appeal_id=row["appeal_id"],
                        object_ref=obj_ref,
                        file_name=fname,
                        mime_type=str(row["media_type"] or "application/octet-stream"),
                        byte_size=int(row["byte_size"] or 0),
                        object_hash=str(row["object_hash"]).strip(),
                        data_classification=row["data_classification"],
                        created_at=row["created_at"],
                    )
                )
            return result

    def _event(
        self,
        cursor: Any,
        *,
        appeal: Appeal,
        event_type: str,
        actor_type: str,
        actor_token: str,
        correlation_id: str,
        payload: dict[str, Any],
        occurred_at: datetime | None = None,
        occurred_at_quality: str = "missing",
        source_system_id: UUID | None = None,
        source_event_id: str | None = None,
    ) -> UUID:
        event_id = uuid4()
        observed_at = _now()
        cursor.execute(
            """
            INSERT INTO appeals.appeal_event
                (event_id, appeal_id, source_system_id, source_event_id, event_type,
                 event_version, occurred_at, occurred_at_quality, observed_at,
                 actor_type, actor_id_token, correlation_id, payload)
            VALUES (%s, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING event_id
            """,
            (
                event_id,
                appeal.request_id,
                source_system_id,
                source_event_id,
                event_type,
                occurred_at,
                occurred_at_quality,
                observed_at,
                actor_type,
                actor_token,
                correlation_id,
                self._json(payload),
            ),
        )
        return event_id

    def _audit(
        self,
        cursor: Any,
        *,
        action: str,
        aggregate_id: UUID,
        region_id: str,
        actor_type: str,
        actor_token: str,
        correlation_id: str,
        payload: dict[str, Any],
        before: object | None = None,
        after: object | None = None,
    ) -> UUID:
        event_id = uuid4()
        before_hash = (
            sha256(self._json(before).encode()).hexdigest() if before is not None else None
        )
        after_hash = sha256(self._json(after).encode()).hexdigest() if after is not None else None
        cursor.execute(
            """
            INSERT INTO audit.audit_event
                (event_id, actor_type, actor_id_token, action, aggregate_type,
                 aggregate_id, region_id, correlation_id, observed_at,
                 before_hash, after_hash, payload)
            VALUES (%s, %s, %s, %s, 'appeal', %s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                event_id,
                actor_type,
                actor_token,
                action,
                str(aggregate_id),
                region_id,
                correlation_id,
                _now(),
                before_hash,
                after_hash,
                self._json(payload),
            ),
        )
        return event_id

    def _outbox(
        self,
        cursor: Any,
        *,
        event_type: str,
        appeal: Appeal,
        aggregate_version: int,
        region_id: str,
        correlation_id: str,
        payload: dict[str, Any],
        data_classification: str = "internal",
        occurred_at: datetime | None = None,
        occurred_at_quality: str = "missing",
    ) -> UUID:
        event_id = uuid4()
        cursor.execute(
            """
            INSERT INTO integration.outbox
                (event_id, event_type, event_version, aggregate_type, subject_id,
                 aggregate_version, region_id, occurred_at, occurred_at_quality,
                 observed_at, producer, correlation_id, data_classification, payload)
            VALUES (%s, %s, 1, 'appeal', %s, %s, %s, %s, %s, %s,
                    'core-api', %s, %s, %s::jsonb)
            """,
            (
                event_id,
                event_type,
                str(appeal.request_id),
                aggregate_version,
                region_id,
                occurred_at,
                occurred_at_quality,
                _now(),
                correlation_id,
                data_classification,
                self._json(payload),
            ),
        )
        return event_id

    def create(
        self,
        command: CreateRequest,
        *,
        idempotency_key: str,
        region_id: str,
        actor: str = "system",
        correlation_id: str = "local-correlation",
    ) -> tuple[Appeal, bool]:
        self._scope(command.region_id, region_id)
        settings = get_settings()
        if settings.effective_profile == "demo" and (
            not command.source_system.endswith("-synthetic")
            or command.consent_or_legal_basis != "SYNTHETIC_TEST_ONLY"
        ):
            raise ManualPathError(
                "demo_synthetic_required",
                "Demo accepts explicitly labelled synthetic appeals only.",
                422,
            )
        operational_profile = settings.environment in {"pilot", "production"}
        if operational_profile and not command.source_payload_ref:
            raise ManualPathError(
                "source_payload_ref_required",
                "An immutable approved source payload reference is required.",
                422,
            )
        if operational_profile and (
            not settings.approved_legal_basis or not settings.approved_retention_class
        ):
            raise ManualPathError(
                "governance_policy_required",
                "Approved legal basis and retention class are required for operational intake.",
                503,
            )
        legal_basis = (
            settings.approved_legal_basis
            if operational_profile
            else command.consent_or_legal_basis or "SYNTHETIC_TEST_ONLY"
        )
        retention_class = (
            settings.approved_retention_class if operational_profile else "synthetic-test"
        )
        body = command.model_dump(mode="json")
        request_hash = _hash(body)
        scope = f"requests:create:{region_id}"
        with self.repository.connection() as connection, connection.cursor() as cursor:
            prior = self._idempotency(cursor, scope, idempotency_key, request_hash)
            if prior is not None:
                return Appeal.model_validate(prior), True

            source_system_id = self._source_system(cursor, command)
            schema_id = self._source_schema(cursor, source_system_id, _now())
            cursor.execute(
                """
                SELECT a.*, ss.system_code AS source_system, sr.raw_payload_ref,
                       ac.redacted_text, ST_Y(a.location::geometry) AS latitude,
                       ST_X(a.location::geometry) AS longitude
                FROM appeals.appeal AS a
                JOIN integration.source_system AS ss ON ss.id = a.source_system_id
                JOIN integration.source_record AS sr ON sr.id = a.source_record_id
                LEFT JOIN privacy.appeal_content AS ac ON ac.appeal_id = a.request_id
                WHERE a.source_system_id = %s AND a.source_request_id = %s
                FOR UPDATE OF a
                """,
                (source_system_id, command.source_request_id),
            )
            existing = cursor.fetchone()
            raw_hash = sha256(self._json(body).encode()).hexdigest()
            if existing is not None:
                if existing["raw_payload_hash"] != raw_hash:
                    raise ManualPathError(
                        "source_identity_conflict",
                        "The source identity has a different request body.",
                    )
                appeal = self._appeal_from_row(existing)
                self._save_idempotency(
                    cursor,
                    scope,
                    idempotency_key,
                    request_hash,
                    appeal.model_dump(mode="json"),
                    resource_id=appeal.request_id,
                )
                return appeal, True

            observed_at = _now()
            request_id = uuid4()
            cursor.execute(
                """
                INSERT INTO integration.import_run
                    (source_system_id, region_id, export_id, source_file_ref,
                     source_checksum, parser_version, mapping_version, row_count,
                     accepted_count, observed_at, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 1, %s, 'completed')
                RETURNING id
                """,
                (
                    source_system_id,
                    command.region_id,
                    f"manual:{idempotency_key}",
                    command.source_payload_ref or f"manual://source-record/{raw_hash}",
                    raw_hash,
                    "manual-path/1.0.0",
                    self.repository.mapping_version,
                    observed_at,
                ),
            )
            import_run = cursor.fetchone()
            if import_run is None:
                raise RuntimeError("manual import run insert returned no id")
            raw_ref = command.source_payload_ref or f"manual://source-record/{raw_hash}"
            pii_flags = []
            if command.text:
                pii_flags.append("free_text")
            if command.location and command.location.address_text_private_ref:
                pii_flags.append("address")
            if not pii_flags:
                pii_flags.append("none")
            canonical_payload = {
                "schema_version": "1.0.0",
                "request_id": str(request_id),
                "source": {
                    "system": command.source_system,
                    "request_id": command.source_request_id,
                    "region_id": command.region_id,
                },
                "intake": {
                    "channel": command.channel,
                    "language": command.language,
                    "raw_text_ref": raw_ref if command.text else None,
                    "transcript_ref": command.transcript_ref,
                    "media_refs": command.media_refs,
                    "citizen_token": command.citizen_token,
                },
                "time": {
                    "received_at": command.received_at.isoformat() if command.received_at else None,
                    "received_at_quality": command.received_at_quality,
                    "source_timezone": command.source_timezone,
                    "observed_at": observed_at.isoformat(),
                },
                "governance": {
                    "legal_basis": legal_basis,
                    "retention_class": retention_class,
                    "pii_flags": pii_flags,
                    "access_scope": [command.region_id],
                    "redaction_version": "basic-pii-redaction/1.0.0"
                    if command.text and not operational_profile
                    else None,
                },
                "ingestion": {
                    "adapter_id": "manual-intake",
                    "adapter_version": self.repository.schema_version,
                    "schema_mapping_version": self.repository.mapping_version,
                    "ingested_at": observed_at.isoformat(),
                    "raw_payload_ref": raw_ref,
                    "validation_status": "accepted",
                },
            }
            if command.location is not None:
                canonical_payload["location"] = {
                    "address_private_ref": command.location.address_text_private_ref,
                    "geo_id": command.location.geo_id,
                    "object_id": command.location.object_id,
                    "latitude": command.location.latitude,
                    "longitude": command.location.longitude,
                    "precision_m": command.location.precision_m,
                }
            cursor.execute(
                """
                INSERT INTO integration.source_record
                    (import_run_id, source_system_id, source_schema_version_id,
                     source_request_id, source_row_ref, raw_payload_ref, raw_payload_hash,
                      canonical_payload, validation_status, occurred_at, observed_at,
                      source_timezone, time_quality)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb,
                        'accepted', %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    import_run["id"],
                    source_system_id,
                    schema_id,
                    command.source_request_id,
                    f"manual:{command.source_system}:{command.source_request_id}",
                    raw_ref,
                    raw_hash,
                    self._json(canonical_payload),
                    command.received_at,
                    observed_at,
                    command.source_timezone,
                    command.received_at_quality,
                ),
            )
            source_record = cursor.fetchone()
            if source_record is None:
                raise RuntimeError("manual source record insert returned no id")

            location = command.location
            values = [
                request_id,
                source_record["id"],
                source_system_id,
                command.source_request_id,
                command.region_id,
                command.channel,
                command.language,
                "new",
                1,
                observed_at,
                command.received_at,
                command.source_timezone,
                command.received_at,
                command.received_at_quality,
                command.received_at_quality,
                command.citizen_token,
                location.address_text_private_ref if location else None,
                command.transcript_ref,
                location.geo_id if location else None,
                location.object_id if location else None,
                location.precision_m if location else None,
                "missing"
                if location is None
                else "exact"
                if location.geo_id or location.object_id
                else "missing",
                legal_basis,
                retention_class,
                "basic-pii-redaction/1.0.0" if command.text and not operational_profile else None,
                self._json(command.media_refs),
            ]
            if location and location.latitude is not None and location.longitude is not None:
                cursor.execute(
                    """
                    INSERT INTO appeals.appeal
                        (request_id, source_record_id, source_system_id, source_request_id,
                         region_id, channel, language, status, version, observed_at,
                         occurred_at, source_timezone, received_at, received_at_quality,
                         time_quality, citizen_token, address_private_ref,
                         transcript_ref, geo_id, object_id, precision_m, normalization_status,
                         legal_basis, retention_class, redaction_version, media_refs, location)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography)
                    RETURNING request_id
                    """,
                    [*values, location.longitude, location.latitude],
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO appeals.appeal
                        (request_id, source_record_id, source_system_id, source_request_id,
                         region_id, channel, language, status, version, observed_at,
                         occurred_at, source_timezone, received_at, received_at_quality,
                         time_quality, citizen_token, address_private_ref,
                         transcript_ref, geo_id, object_id, precision_m, normalization_status,
                         legal_basis, retention_class, redaction_version, media_refs)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s)
                    RETURNING request_id
                    """,
                    values,
                )
            cursor.fetchone()
            # The local regex is only a synthetic fixture aid. Operational
            # requests keep their original text at the approved private ref;
            # no unverified free text enters a feature or inference store.
            redacted = (
                _redact_text(command.text) if command.text and not operational_profile else None
            )
            if redacted is not None:
                cursor.execute(
                    "INSERT INTO privacy.appeal_content (appeal_id, redacted_text) VALUES (%s, %s)",
                    (request_id, redacted),
                )
            appeal = self._appeal(cursor, request_id)
            payload = {
                "source_system": appeal.source_system,
                "source_request_id": appeal.source_request_id,
                "channel": appeal.channel,
                "language": appeal.language,
                "received_at_quality": command.received_at_quality,
            }
            self._event(
                cursor,
                appeal=appeal,
                event_type="appeal.created.v1",
                actor_type="system",
                actor_token=actor,
                correlation_id=correlation_id,
                payload=payload,
                occurred_at=command.received_at,
                occurred_at_quality=command.received_at_quality,
            )
            self._audit(
                cursor,
                action="appeal.created",
                aggregate_id=request_id,
                region_id=region_id,
                actor_type="system",
                actor_token=actor,
                correlation_id=correlation_id,
                payload={"status": "new"},
                after={"request_id": str(request_id), "version": 1, "status": "new"},
            )
            self._outbox(
                cursor,
                event_type="appeal.created.v1",
                appeal=appeal,
                aggregate_version=1,
                region_id=region_id,
                correlation_id=correlation_id,
                payload=payload,
                occurred_at=command.received_at,
                occurred_at_quality=command.received_at_quality,
            )
            self._save_idempotency(
                cursor,
                scope,
                idempotency_key,
                request_hash,
                appeal.model_dump(mode="json"),
                resource_id=request_id,
                response_status=201,
            )
            return appeal, False

    def detail(self, request_id: UUID, *, region_id: str) -> AppealDetail:
        with self.repository.connection() as connection, connection.cursor() as cursor:
            appeal = self._appeal(cursor, request_id)
            self._scope(appeal.region_id, region_id)
            cursor.execute(
                """
                SELECT * FROM appeals.appeal_event
                WHERE appeal_id = %s
                ORDER BY observed_at, event_id
                """,
                (request_id,),
            )
            timeline = [TimelineEvent.model_validate(row) for row in cursor.fetchall()]
            cursor.execute(
                """
                SELECT * FROM triage.operator_decision
                WHERE request_id = %s
                ORDER BY decided_at DESC
                LIMIT 1
                """,
                (request_id,),
            )
            row = cursor.fetchone()
            decision = None
            if row:
                decision = OperatorDecision(
                    request_version=row["request_version"],
                    recommendation_id=row["recommendation_id"],
                    topic_id=row["topic_id"],
                    service_id=row["service_id"],
                    priority=row["priority"],
                    action=row["action"],
                    correction_reason=row["correction_reason"],
                    operator_note=row["operator_note"],
                )
            cursor.execute(
                """
                SELECT o.status, o.region_id, d.external_id, d.attempted_at
                FROM integration.outbox o
                LEFT JOIN LATERAL (
                    SELECT external_id, attempted_at
                    FROM integration.delivery_attempt
                    WHERE outbox_event_id = o.event_id
                    ORDER BY attempt_number DESC LIMIT 1
                ) d ON true
                WHERE o.subject_id = %s ORDER BY o.created_at DESC LIMIT 1
                """,
                (str(request_id),),
            )
            sync_row = cursor.fetchone()
            sync = None
            if sync_row:
                sync = SyncState(
                    status=sync_status_from_outbox(sync_row["status"]),
                    source_system=None,
                    last_attempt_at=sync_row["attempted_at"],
                    external_id=sync_row["external_id"],
                )
            return AppealDetail(
                **appeal.model_dump(),
                timeline=timeline,
                current_decision=decision,
                synchronization=sync,
            )

    def classify(
        self,
        request_id: UUID,
        command: ClassificationInput,
        *,
        idempotency_key: str,
        region_id: str,
        correlation_id: str,
    ) -> ClassificationRecommendation:
        request_hash = _hash(command.model_dump(mode="json"))
        with self.repository.connection() as connection, connection.cursor() as cursor:
            appeal = self._appeal(cursor, request_id, lock=True)
            self._scope(appeal.region_id, region_id)
            prior = self._idempotency(
                cursor, f"classification:{request_id}", idempotency_key, request_hash
            )
            if prior is not None:
                return ClassificationRecommendation.model_validate(prior)
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
            if get_settings().environment in {"pilot", "production"}:
                raise ManualPathError(
                    "privacy_feature_unavailable",
                    "An approved de-identified feature snapshot is not configured.",
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
                    redacted_text=appeal.text or "[NO_TEXT]",
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
            cursor.execute(
                """
                INSERT INTO triage.recommendation
                    (recommendation_id, request_id, request_version, model_name, model_alias,
                     model_version, artifact_sha256, input_contract_version, preprocess_version,
                     taxonomy_version, feature_snapshot_id, confidence_band, confidence,
                     ood_state, ood_score, fallback_mode, rule_hits, evidence_refs,
                     trace_id, correlation_id, latency_ms, produced_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s)
                """,
                (
                    response.recommendation_id,
                    request_id,
                    appeal.version,
                    response.model_name,
                    response.model_alias,
                    response.model_version,
                    response.artifact_sha256,
                    response.input_contract_version,
                    response.preprocess_version,
                    response.taxonomy_version,
                    response.feature_snapshot_id,
                    response.confidence_band,
                    response.confidence,
                    response.ood_state,
                    response.ood_score,
                    response.fallback_mode,
                    self._json(list(response.rule_hits)),
                    self._json(list(response.evidence_refs)),
                    response.trace_id,
                    response.correlation_id,
                    response.latency_ms,
                    response.produced_at,
                ),
            )
            for kind, labels in (
                ("topic", response.top_topics),
                ("service", response.top_services),
            ):
                for item in labels:
                    cursor.execute(
                        """
                        INSERT INTO triage.recommendation_candidate
                            (recommendation_id, candidate_kind, candidate_id, rank, score)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (response.recommendation_id, kind, item.id, item.rank, item.score),
                    )
            payload = {
                "recommendation_id": str(response.recommendation_id),
                "model_version": response.model_version,
                "taxonomy_version": response.taxonomy_version,
                "confidence": response.confidence,
                "ood_score": response.ood_score,
            }
            system_actor = "core-api"
            self._audit(
                cursor,
                action="ai.recommendation.produced",
                aggregate_id=request_id,
                region_id=region_id,
                actor_type="system",
                actor_token=system_actor,
                correlation_id=correlation_id,
                payload=payload,
            )
            self._outbox(
                cursor,
                event_type="ai.classification.produced.v1",
                appeal=appeal,
                aggregate_version=appeal.version,
                region_id=region_id,
                correlation_id=correlation_id,
                payload=payload,
            )
            stored = recommendation.model_dump(mode="json")
            self._save_idempotency(
                cursor,
                f"classification:{request_id}",
                idempotency_key,
                request_hash,
                stored,
                resource_id=response.recommendation_id,
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
        correlation_id: str = "local-correlation",
    ) -> DecisionReceipt:
        request_hash = _hash(command.model_dump(mode="json"))
        scope = f"decision:{request_id}"
        with self.repository.connection() as connection, connection.cursor() as cursor:
            appeal = self._appeal(cursor, request_id, lock=True)
            self._scope(appeal.region_id, region_id)
            prior = self._idempotency(cursor, scope, idempotency_key, request_hash)
            if prior is not None:
                return DecisionReceipt.model_validate(prior)
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
            if command.recommendation_id is not None:
                cursor.execute(
                    """
                    SELECT recommendation_id, feature_snapshot_id
                    FROM triage.recommendation
                    WHERE recommendation_id = %s AND request_id = %s
                      AND request_version = %s
                    """,
                    (command.recommendation_id, request_id, appeal.version),
                )
                if cursor.fetchone() is None:
                    raise ManualPathError(
                        "recommendation_not_found", "The recommendation does not exist.", 422
                    )
            decision_id, new_version = uuid4(), appeal.version + 1
            decided_at = _now()
            cursor.execute(
                """
                INSERT INTO triage.operator_decision
                    (decision_id, request_id, request_version, new_version, recommendation_id,
                     topic_id, service_id, priority, action, correction_reason, operator_note,
                     operator_token, region_id, idempotency_key, correlation_id, decided_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    decision_id,
                    request_id,
                    appeal.version,
                    new_version,
                    command.recommendation_id,
                    command.topic_id,
                    command.service_id,
                    command.priority,
                    command.action,
                    command.correction_reason,
                    command.operator_note,
                    actor,
                    region_id,
                    idempotency_key,
                    correlation_id,
                    decided_at,
                ),
            )
            cursor.execute(
                """
                UPDATE appeals.appeal
                SET status = 'triage', version = %s
                WHERE request_id = %s AND version = %s
                """,
                (new_version, request_id, appeal.version),
            )
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
            current = self._appeal(cursor, request_id)
            self._event(
                cursor,
                appeal=current,
                event_type="appeal.decision.recorded.v1",
                actor_type="operator",
                actor_token=actor,
                correlation_id=correlation_id,
                payload=payload,
            )
            audit_id = self._audit(
                cursor,
                action="appeal.decision.recorded",
                aggregate_id=request_id,
                region_id=region_id,
                actor_type="operator",
                actor_token=actor,
                correlation_id=correlation_id,
                payload=payload,
                before={"version": appeal.version},
                after={"version": new_version, "status": "triage"},
            )
            self._outbox(
                cursor,
                event_type="appeal.decision.recorded.v1",
                appeal=current,
                aggregate_version=new_version,
                region_id=region_id,
                correlation_id=correlation_id,
                payload=payload,
            )
            receipt = DecisionReceipt(
                decision_id=decision_id,
                request_id=request_id,
                new_version=new_version,
                audit_event_id=audit_id,
            )
            self._save_idempotency(
                cursor,
                scope,
                idempotency_key,
                request_hash,
                receipt.model_dump(mode="json"),
                resource_id=decision_id,
                response_status=201,
            )
            return receipt

    def status(
        self,
        request_id: UUID,
        command: StatusEventInput,
        *,
        idempotency_key: str,
        region_id: str,
        actor: str,
        correlation_id: str = "local-correlation",
    ) -> TimelineEvent:
        request_hash = _hash(command.model_dump(mode="json"))
        scope = f"status:{request_id}"
        with self.repository.connection() as connection, connection.cursor() as cursor:
            appeal = self._appeal(cursor, request_id, lock=True)
            self._scope(appeal.region_id, region_id)
            prior = self._idempotency(cursor, scope, idempotency_key, request_hash)
            if prior is not None:
                return TimelineEvent.model_validate(prior)
            cursor.execute(
                "SELECT id FROM integration.source_system WHERE system_code = %s",
                (command.source_system,),
            )
            source = cursor.fetchone()
            source_system_id = source["id"] if source else None
            if source_system_id is None and get_settings().effective_profile in {
                "pilot",
                "production",
            }:
                raise ManualPathError(
                    "unknown_source_system", "Status source is not registered for review.", 422
                )
            cursor.execute(
                """
                SELECT * FROM appeals.appeal_event
                WHERE source_system_id IS NOT DISTINCT FROM %s AND source_event_id = %s
                  AND (source_system_id IS NOT NULL OR payload->>'source_system' = %s)
                """,
                (source_system_id, command.source_event_id, command.source_system),
            )
            duplicate = cursor.fetchone()
            if duplicate:
                payload = self._load_json(duplicate["payload"], {})
                if duplicate["appeal_id"] != request_id or (
                    payload.get("new_status") != command.status
                    or payload.get("source_system") != command.source_system
                    or payload.get("reason_code") != command.reason_code
                    or payload.get("evidence_refs") != command.evidence_refs
                    or duplicate["occurred_at"] != command.occurred_at
                    or duplicate["occurred_at_quality"] != command.occurred_at_quality
                ):
                    raise ManualPathError(
                        "source_event_conflict",
                        "Source event ID was already used for a different appeal or status.",
                        409,
                    )
                event = TimelineEvent.model_validate(duplicate)
                self._save_idempotency(
                    cursor,
                    scope,
                    idempotency_key,
                    request_hash,
                    event.model_dump(mode="json"),
                    resource_id=event.event_id,
                )
                return event
            new_version = appeal.version + 1
            cursor.execute(
                """
                UPDATE appeals.appeal
                SET status = %s, version = %s
                WHERE request_id = %s AND version = %s
                """,
                (command.status, new_version, request_id, appeal.version),
            )
            current = self._appeal(cursor, request_id)
            payload = {
                "previous_status": appeal.status,
                "new_status": command.status,
                "source_event_id": command.source_event_id,
                "source_system": command.source_system,
                "source_timezone": command.source_timezone,
                "reason_code": command.reason_code,
                "evidence_refs": command.evidence_refs,
            }
            event_id = self._event(
                cursor,
                appeal=current,
                event_type="appeal.status.changed.v1",
                actor_type="operator",
                actor_token=actor,
                correlation_id=correlation_id,
                payload=payload,
                occurred_at=command.occurred_at,
                occurred_at_quality=command.occurred_at_quality,
                source_system_id=source_system_id,
                source_event_id=command.source_event_id,
            )
            cursor.execute("SELECT * FROM appeals.appeal_event WHERE event_id = %s", (event_id,))
            event = TimelineEvent.model_validate(cursor.fetchone())
            self._audit(
                cursor,
                action="appeal.status.changed",
                aggregate_id=request_id,
                region_id=region_id,
                actor_type="operator",
                actor_token=actor,
                correlation_id=correlation_id,
                payload=payload,
                before={"version": appeal.version, "status": appeal.status},
                after={"version": new_version, "status": command.status},
            )
            self._outbox(
                cursor,
                event_type="appeal.status.changed.v1",
                appeal=current,
                aggregate_version=new_version,
                region_id=region_id,
                correlation_id=correlation_id,
                payload=payload,
                occurred_at=command.occurred_at,
                occurred_at_quality=command.occurred_at_quality,
            )
            self._save_idempotency(
                cursor,
                scope,
                idempotency_key,
                request_hash,
                event.model_dump(mode="json"),
                resource_id=event_id,
                response_status=201,
            )
            return event

    def assign(
        self,
        request_id: UUID,
        command: AssignmentCommand,
        *,
        idempotency_key: str,
        region_id: str,
        actor: str,
        correlation_id: str = "local-correlation",
        override_authorized: bool = False,
    ) -> SyncReceipt:
        request_hash = _hash(command.model_dump(mode="json"))
        scope = f"assignment:{request_id}"
        with self.repository.connection() as connection, connection.cursor() as cursor:
            appeal = self._appeal(cursor, request_id, lock=True)
            self._scope(appeal.region_id, region_id)
            prior = self._idempotency(cursor, scope, idempotency_key, request_hash)
            if prior is not None:
                return SyncReceipt.model_validate(prior)
            if appeal.version != command.request_version:
                raise ManualPathError(
                    "stale_version", "The appeal changed since the operator opened it."
                )
            if command.handoff_override_reason_code and not override_authorized:
                raise ManualPathError(
                    "handoff_override_forbidden",
                    "A supervisor or administrator must authorize the handoff override.",
                    403,
                )
            loop_risk = False
            if command.assignee_unit_id is not None:
                cursor.execute(
                    """SELECT EXISTS (
                           SELECT 1 FROM ownership.handoff_outcome AS outcome
                           WHERE outcome.region_id = %s AND outcome.request_id = %s
                             AND outcome.disposition = 'rejected'
                             AND (
                               outcome.organization_id = %s
                               OR EXISTS (
                                 SELECT 1 FROM ownership.unit_organization_mapping AS mapping
                                 JOIN ownership.organization_version AS org
                                   ON org.region_id = mapping.region_id
                                  AND org.organization_id = mapping.organization_id
                                  AND org.version = mapping.organization_version
                                 WHERE mapping.region_id = %s AND mapping.service_id = %s
                                   AND mapping.unit_id = %s
                                   AND mapping.organization_id = outcome.organization_id
                                   AND mapping.state = 'approved' AND org.state = 'approved'
                                   AND NOT mapping.synthetic_only AND NOT org.synthetic_only
                                   AND mapping.effective_from <= now()
                                   AND (mapping.effective_to IS NULL
                                        OR mapping.effective_to > now())
                                   AND org.effective_from <= now()
                                   AND (org.effective_to IS NULL OR org.effective_to > now())
                               )
                             )
                       ) AS loop_risk""",
                    (
                        region_id,
                        request_id,
                        command.assignee_unit_id,
                        region_id,
                        command.service_id,
                        command.assignee_unit_id,
                    ),
                )
                loop_result = cursor.fetchone()
                loop_risk = bool(loop_result and loop_result["loop_risk"])
            if loop_risk and command.handoff_override_reason_code is None:
                raise ManualPathError(
                    "handoff_loop_requires_supervisor",
                    "This organization rejected the appeal before; "
                    "a supervisor must review the handoff.",
                    409,
                )
            if not loop_risk and command.handoff_override_reason_code is not None:
                raise ManualPathError(
                    "handoff_override_not_required",
                    "No prior rejection supports a handoff override for this assignee.",
                    409,
                )
            new_version = appeal.version + 1
            payload = {
                "source_system": appeal.source_system,
                "service_id": command.service_id,
                "assignee_unit_id": command.assignee_unit_id,
                "reason_code": command.reason_code,
                "handoff_loop_overridden": loop_risk,
                "handoff_override_reason_code": command.handoff_override_reason_code,
                "policy_version": command.policy_version,
                "due_at": command.expected_due_at.isoformat() if command.expected_due_at else None,
            }
            cursor.execute(
                """
                UPDATE appeals.appeal
                SET status = 'assigned', version = %s
                WHERE request_id = %s AND version = %s
                """,
                (new_version, request_id, appeal.version),
            )
            current = self._appeal(cursor, request_id)
            self._event(
                cursor,
                appeal=current,
                event_type="appeal.assigned.v1",
                actor_type="operator",
                actor_token=actor,
                correlation_id=correlation_id,
                payload=payload,
            )
            self._audit(
                cursor,
                action="appeal.assigned",
                aggregate_id=request_id,
                region_id=region_id,
                actor_type="operator",
                actor_token=actor,
                correlation_id=correlation_id,
                payload=payload,
                before={"version": appeal.version, "status": appeal.status},
                after={"version": new_version, "status": "assigned"},
            )
            outbox_id = self._outbox(
                cursor,
                event_type="appeal.assigned.v1",
                appeal=current,
                aggregate_version=new_version,
                region_id=region_id,
                correlation_id=correlation_id,
                payload=payload,
            )
            cursor.execute(
                """
                INSERT INTO appeals.assignment
                    (request_id, request_version, new_version, to_service_id, assignee_unit_id,
                     reason_code, expected_due_at, policy_version, actor_token, region_id,
                     idempotency_key, correlation_id, outbox_event_id, assigned_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    request_id,
                    appeal.version,
                    new_version,
                    command.service_id,
                    command.assignee_unit_id,
                    command.reason_code,
                    command.expected_due_at,
                    command.policy_version,
                    actor,
                    region_id,
                    idempotency_key,
                    correlation_id,
                    outbox_id,
                    _now(),
                ),
            )
            receipt = SyncReceipt(outbox_event_id=outbox_id, status="queued")
            self._save_idempotency(
                cursor,
                scope,
                idempotency_key,
                request_hash,
                receipt.model_dump(mode="json"),
                resource_id=outbox_id,
                response_status=202,
            )
            return receipt

    def latest_assignment(self, request_id: UUID, *, region_id: str) -> LatestAssignment:
        with self.repository.connection() as connection, connection.cursor() as cursor:
            appeal = self._appeal(cursor, request_id)
            self._scope(appeal.region_id, region_id)
            cursor.execute(
                """SELECT assignment_id, request_id, request_version, new_version,
                          to_service_id AS service_id, assignee_unit_id, assigned_at
                   FROM appeals.assignment
                   WHERE request_id = %s AND region_id = %s
                   ORDER BY assigned_at DESC, assignment_id DESC LIMIT 1""",
                (request_id, region_id),
            )
            row = cursor.fetchone()
        if row is None:
            raise ManualPathError("assignment_not_found", "No assignment is recorded.", 404)
        return LatestAssignment.model_validate(row)

    def list_services(self, *, region_id: str, effective_at: datetime) -> list[ServiceDefinition]:
        with self.repository.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT s.*, COALESCE(jsonb_agg(st.topic_id ORDER BY st.topic_id)
                    FILTER (WHERE st.topic_id IS NOT NULL), '[]'::jsonb) AS topic_ids
                FROM catalog.service_version s
                LEFT JOIN catalog.service_topic st ON st.service_id = s.service_id
                    AND st.region_id = s.region_id AND st.service_version = s.version
                WHERE s.region_id = %s AND s.active AND s.effective_from <= %s
                    AND (s.effective_to IS NULL OR s.effective_to > %s)
                GROUP BY s.service_id, s.region_id, s.version
                ORDER BY s.service_id
                """,
                (region_id, effective_at, effective_at),
            )
            return [
                ServiceDefinition(
                    service_id=row["service_id"],
                    region_id=row["region_id"],
                    version=row["version"],
                    effective_from=row["effective_from"],
                    effective_to=row["effective_to"],
                    display_name=self._load_json(row["display_name"], {}),
                    topic_ids=self._load_json(row["topic_ids"], []),
                    required_fields=self._load_json(row["required_fields"], []),
                    active=row["active"],
                    synthetic_only=row["synthetic_only"],
                )
                for row in cursor.fetchall()
            ]
