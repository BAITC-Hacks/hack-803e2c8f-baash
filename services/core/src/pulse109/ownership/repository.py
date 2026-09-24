"""Region-scoped read interface for effective ownership facts."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from .engine import HandoffDisposition, HandoffOutcome, ResponsibilityRule


@dataclass(frozen=True, slots=True)
class AssetResolution:
    status: Literal["verified", "unverified", "conflicting"]
    asset_id: str | None = None
    jurisdiction_id: str | None = None


class OwnershipCatalogConflict(Exception):
    """Approved catalog state is ambiguous or too large to assess safely."""


class OwnershipRepository(Protocol):
    def resolve_asset(
        self, *, region_id: str, asset_id: str, at: datetime, allow_synthetic: bool
    ) -> AssetResolution: ...

    def list_rules(
        self, *, region_id: str, service_id: str, at: datetime, allow_synthetic: bool
    ) -> list[ResponsibilityRule]: ...

    def list_outcomes(self, *, region_id: str, request_id: UUID) -> list[HandoffOutcome]: ...


class EmptyOwnershipRepository:
    """Local fallback with no invented ownership facts."""

    def resolve_asset(
        self, *, region_id: str, asset_id: str, at: datetime, allow_synthetic: bool
    ) -> AssetResolution:
        return AssetResolution(status="unverified")

    def list_rules(
        self, *, region_id: str, service_id: str, at: datetime, allow_synthetic: bool
    ) -> list[ResponsibilityRule]:
        return []

    def list_outcomes(self, *, region_id: str, request_id: UUID) -> list[HandoffOutcome]:
        return []


class PostgresOwnershipRepository:
    """Only approved, effective and region-bound facts may reach the engine."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            yield connection

    def resolve_asset(
        self, *, region_id: str, asset_id: str, at: datetime, allow_synthetic: bool
    ) -> AssetResolution:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.asset_id, a.jurisdiction_id
                FROM ownership.asset_version AS a
                LEFT JOIN ownership.jurisdiction_version AS j
                    ON j.region_id = a.region_id
                   AND j.jurisdiction_id = a.jurisdiction_id
                   AND j.version = a.jurisdiction_version
                WHERE a.region_id = %s AND a.asset_id = %s AND a.state = 'approved'
                  AND a.effective_from <= %s AND (a.effective_to IS NULL OR a.effective_to > %s)
                  AND (%s OR NOT a.synthetic_only)
                  AND (a.jurisdiction_id IS NULL OR
                       (j.state = 'approved' AND j.effective_from <= %s
                        AND (j.effective_to IS NULL OR j.effective_to > %s)
                        AND (%s OR NOT j.synthetic_only)))
                LIMIT 2
                """,
                (region_id, asset_id, at, at, allow_synthetic, at, at, allow_synthetic),
            )
            rows = cursor.fetchall()
        if len(rows) > 1:
            return AssetResolution(status="conflicting")
        if not rows:
            return AssetResolution(status="unverified")
        return AssetResolution(
            status="verified",
            asset_id=rows[0]["asset_id"],
            jurisdiction_id=rows[0]["jurisdiction_id"],
        )

    def list_rules(
        self, *, region_id: str, service_id: str, at: datetime, allow_synthetic: bool
    ) -> list[ResponsibilityRule]:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT r.rule_id, r.version, r.region_id, r.service_id,
                       r.organization_id, r.jurisdiction_id, r.asset_id,
                       r.effective_from, r.effective_to, r.reason_code, r.source_ref
                FROM ownership.responsibility_rule_version AS r
                JOIN catalog.service_version AS s
                    ON s.service_id = r.service_id AND s.region_id = r.region_id
                   AND s.version = r.service_version
                JOIN ownership.organization_version AS o
                    ON o.region_id = r.region_id AND o.organization_id = r.organization_id
                   AND o.version = r.organization_version
                LEFT JOIN ownership.jurisdiction_version AS j
                    ON j.region_id = r.region_id AND j.jurisdiction_id = r.jurisdiction_id
                   AND j.version = r.jurisdiction_version
                LEFT JOIN ownership.asset_version AS a
                    ON a.region_id = r.region_id AND a.asset_id = r.asset_id
                   AND a.version = r.asset_version
                WHERE r.region_id = %s AND r.service_id = %s AND r.state = 'approved'
                  AND r.effective_from <= %s AND (r.effective_to IS NULL OR r.effective_to > %s)
                  AND (%s OR NOT r.synthetic_only)
                  AND s.active AND s.effective_from <= %s
                  AND (s.effective_to IS NULL OR s.effective_to > %s)
                  AND (%s OR NOT s.synthetic_only)
                  AND o.state = 'approved' AND o.effective_from <= %s
                  AND (o.effective_to IS NULL OR o.effective_to > %s)
                  AND (%s OR NOT o.synthetic_only)
                  AND (r.jurisdiction_id IS NULL OR
                       (j.state = 'approved' AND j.effective_from <= %s
                        AND (j.effective_to IS NULL OR j.effective_to > %s)
                        AND (%s OR NOT j.synthetic_only)))
                  AND (r.asset_id IS NULL OR
                       (a.state = 'approved' AND a.effective_from <= %s
                        AND (a.effective_to IS NULL OR a.effective_to > %s)
                        AND (%s OR NOT a.synthetic_only)))
                ORDER BY r.rule_id, r.version
                LIMIT 1001
                """,
                (
                    region_id,
                    service_id,
                    at,
                    at,
                    allow_synthetic,
                    at,
                    at,
                    allow_synthetic,
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
        if len(rows) > 1000:
            raise OwnershipCatalogConflict(
                "approved responsibility rules exceed safe assessment limit"
            )
        return [ResponsibilityRule(**row) for row in rows]

    def list_outcomes(self, *, region_id: str, request_id: UUID) -> list[HandoffOutcome]:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT organization_id, disposition
                FROM ownership.handoff_outcome
                WHERE region_id = %s AND request_id = %s
                """,
                (region_id, request_id),
            )
            rows = cursor.fetchall()
        return [
            HandoffOutcome(
                organization_id=row["organization_id"],
                disposition=HandoffDisposition(row["disposition"]),
            )
            for row in rows
        ]
