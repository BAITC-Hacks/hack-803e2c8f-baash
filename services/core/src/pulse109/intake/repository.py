"""Approved, region-scoped adaptive-intake policy reads."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Protocol

import psycopg
from psycopg.rows import dict_row

from .service import IntakePolicy, RequiredField


class IntakePolicyConflict(Exception):
    """The approved effective policy is absent, overlapping, or malformed."""


class IntakePolicyRepository(Protocol):
    def resolve(
        self,
        *,
        region_id: str,
        service_id: str,
        topic_id: str,
        at: datetime,
        allow_synthetic: bool,
    ) -> IntakePolicy | None: ...


class EmptyIntakePolicyRepository:
    def resolve(
        self,
        *,
        region_id: str,
        service_id: str,
        topic_id: str,
        at: datetime,
        allow_synthetic: bool,
    ) -> IntakePolicy | None:
        return None


class PostgresIntakePolicyRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            yield connection

    def resolve(
        self,
        *,
        region_id: str,
        service_id: str,
        topic_id: str,
        at: datetime,
        allow_synthetic: bool,
    ) -> IntakePolicy | None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.version, p.required_fields
                FROM intake.policy_version AS p
                JOIN catalog.service_version AS s
                  ON s.region_id = p.region_id AND s.service_id = p.service_id
                 AND s.version = p.service_version
                JOIN catalog.topic_version AS t
                  ON t.topic_id = p.topic_id AND t.version = p.topic_version
                WHERE p.region_id = %s AND p.service_id = %s AND p.topic_id = %s
                  AND p.state = 'approved'
                  AND p.effective_from <= %s
                  AND (p.effective_to IS NULL OR p.effective_to > %s)
                  AND (%s OR NOT p.synthetic_only)
                  AND s.active AND s.effective_from <= %s
                  AND (s.effective_to IS NULL OR s.effective_to > %s)
                  AND (%s OR NOT s.synthetic_only)
                  AND t.active AND t.effective_from <= %s
                  AND (t.effective_to IS NULL OR t.effective_to > %s)
                  AND (%s OR NOT t.synthetic_only)
                LIMIT 2
                """,
                (
                    region_id,
                    service_id,
                    topic_id,
                    at,
                    at,
                    allow_synthetic,
                    at,
                    at,
                    allow_synthetic,
                    at,
                    at,
                    allow_synthetic,
                ),
            )
            rows = cursor.fetchall()
        if len(rows) > 1:
            raise IntakePolicyConflict("overlapping approved intake policy versions")
        if not rows:
            return None
        try:
            raw_fields = rows[0]["required_fields"]
            if isinstance(raw_fields, str):
                raw_fields = json.loads(raw_fields)
            if not isinstance(raw_fields, list):
                raise ValueError("required_fields must be an array")
            fields = tuple(
                RequiredField(
                    field_id=item["field_id"],
                    questions=item["questions"],
                    when_states=item.get("when_states", {}),
                    evidence_type=item.get("evidence_type"),
                )
                for item in raw_fields
            )
            return IntakePolicy(
                service_id=service_id,
                topic_id=topic_id,
                version=rows[0]["version"],
                approved=True,
                required_fields=fields,
            )
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise IntakePolicyConflict("approved intake policy payload is invalid") from error
