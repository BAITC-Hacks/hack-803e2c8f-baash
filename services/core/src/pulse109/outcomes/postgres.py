"""PostgreSQL persistence for evidence-backed closure."""

from __future__ import annotations

import json
from hashlib import sha256
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from .models import ClosureConfirmation, ClosurePreflight, ClosureReceipt
from .service import ClosureIntegrityError


class PostgresClosureRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    @staticmethod
    def _json(value: object) -> str:
        return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))

    def create_preflight(
        self,
        *,
        request_id: UUID,
        region_id: str,
        command: ClosurePreflight,
        evidence_hash: str,
        actor: str,
        correlation_id: str,
    ) -> UUID:
        preflight_id = uuid4()
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT region_id, status, version FROM appeals.appeal "
                "WHERE request_id=%s FOR KEY SHARE",
                (request_id,),
            )
            appeal = cur.fetchone()
            if appeal is None or appeal["region_id"] != region_id:
                raise ClosureIntegrityError(
                    "appeal_not_found", "The appeal is not available in this region.", 404
                )
            if appeal["status"] != "resolved":
                raise ClosureIntegrityError(
                    "resolution_required",
                    "A recorded resolution is required before closure evidence can be reviewed.",
                )
            if appeal["version"] != command.expected_appeal_version:
                raise ClosureIntegrityError(
                    "appeal_version_conflict", "The appeal changed; refresh and review it again."
                )
            # Every content hash must resolve to an immutable attachment owned by this appeal.
            refs = [item.reference[7:] for item in command.evidence]
            cur.execute(
                "SELECT object_hash FROM appeals.attachment_ref "
                "WHERE appeal_id=%s AND lower(object_hash)=ANY(%s) FOR KEY SHARE",
                (request_id, refs),
            )
            available = {row["object_hash"].lower() for row in cur.fetchall()}
            if available != set(refs):
                raise ClosureIntegrityError(
                    "evidence_not_found",
                    "One or more evidence items are not attached to this appeal.",
                    422,
                )
            cur.execute(
                """INSERT INTO appeals.closure_preflight
                (preflight_id, request_id, region_id, appeal_version, resolution_code,
                 evidence, evidence_hash, created_by_token, correlation_id)
                VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)""",
                (
                    preflight_id,
                    request_id,
                    region_id,
                    command.expected_appeal_version,
                    command.resolution_code,
                    self._json([r.model_dump(mode="json") for r in command.evidence]),
                    evidence_hash,
                    actor,
                    correlation_id,
                ),
            )
        return preflight_id

    def confirm(
        self,
        *,
        request_id: UUID,
        region_id: str,
        command: ClosureConfirmation,
        actor: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> ClosureReceipt:
        body = command.model_dump(mode="json") | {
            "request_id": str(request_id),
            "region_id": region_id,
        }
        request_hash = sha256(self._json(body).encode()).hexdigest()
        scope = f"appeal-closure:{region_id}:{request_id}:{sha256(actor.encode()).hexdigest()[:24]}"
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                (f"{scope}:{idempotency_key}",),
            )
            cur.execute(
                "SELECT request_hash,response_body FROM integration.idempotency_key "
                "WHERE scope=%s AND idempotency_key=%s FOR UPDATE",
                (scope, idempotency_key),
            )
            previous = cur.fetchone()
            if previous:
                if previous["request_hash"] != request_hash:
                    raise ClosureIntegrityError(
                        "idempotency_conflict", "The idempotency key has a different request body."
                    )
                prior_body = previous["response_body"]
                if isinstance(prior_body, str):
                    prior_body = json.loads(prior_body)
                return ClosureReceipt.model_validate(prior_body | {"replayed": True})
            cur.execute(
                "SELECT region_id,status,version FROM appeals.appeal "
                "WHERE request_id=%s FOR UPDATE",
                (request_id,),
            )
            appeal = cur.fetchone()
            if appeal is None or appeal["region_id"] != region_id:
                raise ClosureIntegrityError(
                    "appeal_not_found", "The appeal is not available in this region.", 404
                )
            cur.execute(
                "SELECT * FROM appeals.closure_preflight "
                "WHERE preflight_id=%s AND request_id=%s AND region_id=%s FOR UPDATE",
                (command.preflight_id, request_id, region_id),
            )
            preflight = cur.fetchone()
            if preflight is None:
                raise ClosureIntegrityError(
                    "preflight_not_found", "A valid closure preflight is required.", 404
                )
            if preflight["evidence_hash"] != command.evidence_hash:
                raise ClosureIntegrityError(
                    "evidence_hash_mismatch", "The evidence changed after preflight.", 422
                )
            if (
                preflight["appeal_version"] != appeal["version"]
                or command.expected_appeal_version != appeal["version"]
            ):
                raise ClosureIntegrityError(
                    "appeal_version_conflict", "The appeal changed after preflight."
                )
            if appeal["status"] != "resolved":
                raise ClosureIntegrityError(
                    "resolution_required", "The appeal must remain resolved until confirmation."
                )
            if preflight["confirmed_at"] is not None:
                raise ClosureIntegrityError(
                    "preflight_already_used", "This preflight has already been consumed."
                )
            closure_id, audit_id, outbox_id, event_id = uuid4(), uuid4(), uuid4(), uuid4()
            payload = {
                "closure_id": str(closure_id),
                "request_id": str(request_id),
                "region_id": region_id,
                "resolution_code": preflight["resolution_code"],
                "evidence_hash": command.evidence_hash,
                "evidence_count": len(preflight["evidence"]),
                "reason_code": command.reason_code,
                "confirmed_by": actor,
            }
            cur.execute(
                "UPDATE appeals.appeal SET status='closed',version=version+1 WHERE request_id=%s",
                (request_id,),
            )
            cur.execute(
                "UPDATE appeals.closure_preflight SET confirmed_at=now(), "
                "closure_id=%s WHERE preflight_id=%s",
                (closure_id, command.preflight_id),
            )
            cur.execute(
                """INSERT INTO appeals.appeal_event
                (event_id,appeal_id,event_type,event_version,occurred_at_quality,
                 observed_at,actor_type,actor_id_token,correlation_id,payload)
                VALUES (%s,%s,'appeal.closed.v1',1,'missing',now(),'operator',%s,%s,%s::jsonb)""",
                (event_id, request_id, actor, correlation_id, self._json(payload)),
            )
            cur.execute(
                """INSERT INTO audit.audit_event
                (event_id,actor_type,actor_id_token,action,aggregate_type,aggregate_id,
                 region_id,reason_code,correlation_id,observed_at,payload)
                VALUES (%s,'operator',%s,'appeal.closed','appeal',%s,%s,%s,%s,now(),%s::jsonb)""",
                (
                    audit_id,
                    actor,
                    str(request_id),
                    region_id,
                    command.reason_code,
                    correlation_id,
                    self._json(payload),
                ),
            )
            cur.execute(
                """INSERT INTO integration.outbox
                (event_id,event_type,event_version,aggregate_type,subject_id,aggregate_version,
                 region_id,occurred_at_quality,observed_at,producer,correlation_id,
                 data_classification,payload)
                VALUES (%s,'appeal.closed.v1',1,'appeal',%s,%s,%s,'missing',now(),
                        'core-api',%s,'internal',%s::jsonb)""",
                (
                    outbox_id,
                    str(request_id),
                    appeal["version"] + 1,
                    region_id,
                    correlation_id,
                    self._json(payload),
                ),
            )
            receipt = ClosureReceipt(
                closure_id=closure_id,
                request_id=request_id,
                region_id=region_id,
                status="closed",
                evidence_hash=command.evidence_hash,
                audit_event_id=audit_id,
                outbox_event_id=outbox_id,
            )
            cur.execute(
                """INSERT INTO integration.idempotency_key
                (scope,idempotency_key,request_hash,resource_id,response_status,response_body)
                VALUES (%s,%s,%s,%s,201,%s::jsonb)""",
                (
                    scope,
                    idempotency_key,
                    request_hash,
                    closure_id,
                    self._json(receipt.model_dump(mode="json")),
                ),
            )
            return receipt
