"""Repositories for private reference storage and immutable access auditing."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Protocol

import psycopg
from psycopg.rows import dict_row

from .models import PIIAccessAudit, PrivateRef


class PrivateRefRepository(Protocol):
    def store(self, ref: PrivateRef) -> None: ...
    def get(self, token: str) -> PrivateRef | None: ...
    def record_access_audit(self, audit: PIIAccessAudit) -> None: ...
    def list_access_audits(self, token: str) -> list[PIIAccessAudit]: ...


class InMemoryPrivateRefRepository:
    def __init__(self) -> None:
        self.refs: dict[str, PrivateRef] = {}
        self.audits: list[PIIAccessAudit] = []

    def store(self, ref: PrivateRef) -> None:
        self.refs[ref.token] = ref

    def get(self, token: str) -> PrivateRef | None:
        return self.refs.get(token)

    def record_access_audit(self, audit: PIIAccessAudit) -> None:
        self.audits.append(audit)

    def list_access_audits(self, token: str) -> list[PIIAccessAudit]:
        return [a for a in self.audits if a.token == token]


class PostgresPrivateRefRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            yield conn

    def store(self, ref: PrivateRef) -> None:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO privacy.private_ref
                    (token, vault_ref, classification, access_scope, retention_class,
                     created_at, deletion_due_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (token) DO UPDATE SET
                    vault_ref = EXCLUDED.vault_ref,
                    classification = EXCLUDED.classification,
                    access_scope = EXCLUDED.access_scope,
                    retention_class = EXCLUDED.retention_class,
                    deletion_due_at = EXCLUDED.deletion_due_at
                """,
                (
                    ref.token,
                    ref.vault_ref,
                    ref.classification,
                    ref.access_scope,
                    ref.retention_class,
                    ref.created_at,
                    ref.deletion_due_at,
                ),
            )
            conn.commit()

    def get(self, token: str) -> PrivateRef | None:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT token, vault_ref, classification, access_scope, retention_class,
                       created_at, deletion_due_at
                FROM privacy.private_ref
                WHERE token = %s
                """,
                (token,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return PrivateRef(
                token=str(row["token"]),
                vault_ref=str(row["vault_ref"]),
                classification=row["classification"],
                access_scope=list(row["access_scope"]),
                retention_class=str(row["retention_class"]),
                created_at=row["created_at"],
                deletion_due_at=row["deletion_due_at"],
            )

    def record_access_audit(self, audit: PIIAccessAudit) -> None:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit.audit_event
                    (event_id, actor_type, actor_id_token, action, aggregate_type,
                     aggregate_id, region_id, reason_code, observed_at, payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    audit.audit_event_id,
                    "operator",
                    audit.actor_token,
                    audit.action,
                    "privacy.private_ref",
                    audit.token,
                    audit.region_id,
                    audit.reason_code,
                    audit.observed_at,
                    json.dumps(audit.payload),
                ),
            )
            conn.commit()

    def list_access_audits(self, token: str) -> list[PIIAccessAudit]:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_id, actor_id_token, action, aggregate_id, region_id,
                       reason_code, observed_at, payload
                FROM audit.audit_event
                WHERE aggregate_type = 'privacy.private_ref' AND aggregate_id = %s
                ORDER BY observed_at ASC
                """,
                (token,),
            )
            rows = cur.fetchall()
            audits: list[PIIAccessAudit] = []
            for row in rows:
                payload = row["payload"]
                if isinstance(payload, str):
                    payload = json.loads(payload)
                audits.append(
                    PIIAccessAudit(
                        audit_event_id=row["event_id"],
                        action=row["action"],
                        token=str(row["aggregate_id"]),
                        actor_token=str(row["actor_id_token"]),
                        region_id=row["region_id"],
                        reason_code=str(row["reason_code"]),
                        observed_at=row["observed_at"],
                        payload=payload or {},
                    )
                )
            return audits
