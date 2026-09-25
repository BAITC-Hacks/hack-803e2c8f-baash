"""Opt-in read-only Handoff Guard operational metrics."""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

import psycopg
from psycopg.rows import dict_row


@dataclass(frozen=True, slots=True)
class HandoffMetricsQuery:
    """A region and an explicit UTC assignment-cohort interval [start, end)."""

    region_id: str
    start_at: datetime
    end_at: datetime

    def __post_init__(self) -> None:
        if re.fullmatch(r"[A-Z0-9_-]{2,32}", self.region_id) is None:
            raise ValueError("region_id must be 2-32 uppercase letters, digits, '_' or '-'")
        for value in (self.start_at, self.end_at):
            if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
                raise ValueError("metrics interval timestamps must be explicitly UTC")
        if self.start_at >= self.end_at:
            raise ValueError("metrics interval must have start_at before end_at")
        if self.end_at - self.start_at > timedelta(days=366):
            raise ValueError("metrics interval must not exceed 366 days")


@dataclass(frozen=True, slots=True)
class HandoffRate:
    numerator: int
    denominator: int
    numerator_definition: str = ""
    denominator_definition: str = ""

    @property
    def value(self) -> float | None:
        return self.numerator / self.denominator if self.denominator else None


@dataclass(frozen=True, slots=True)
class HandoffMetrics:
    region_id: str
    interval_start: datetime
    interval_end: datetime
    assignment_count: int
    first_pass_acceptance: HandoffRate
    first_pass_unclassified_assignments: int
    repeated_rejected_handoffs: HandoffRate
    unmapped_assignments: int
    provenance: str
    quality_state: str


class HandoffMetricsRepository(Protocol):
    def read_metrics(self, query: HandoffMetricsQuery) -> HandoffMetrics: ...


class PostgresHandoffMetricsRepository:
    """Reads persisted assignments and outcomes; never changes operational state.

    Operational system codes are a required allowlist, so sources used only for
    synthetic fixtures cannot enter a reported operational metric.
    """

    def __init__(
        self, database_url: str, *, operational_source_system_codes: frozenset[str]
    ) -> None:
        if not operational_source_system_codes:
            raise ValueError("operational source-system allowlist must not be empty")
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self.operational_source_system_codes = operational_source_system_codes

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            yield connection

    def read_metrics(self, query: HandoffMetricsQuery) -> HandoffMetrics:
        codes = sorted(self.operational_source_system_codes)
        sql = """
            WITH cohort AS (
                SELECT a.assignment_id, a.request_id, a.region_id,
                       a.request_version, a.new_version,
                       a.to_service_id, a.assignee_unit_id, a.assigned_at,
                       a.new_version = (SELECT min(all_assignments.new_version)
                           FROM appeals.assignment AS all_assignments
                           WHERE all_assignments.request_id = a.request_id)
                           AS is_first_assignment
                FROM appeals.assignment AS a
                JOIN appeals.appeal AS appeal
                  ON appeal.request_id = a.request_id AND appeal.region_id = a.region_id
                JOIN integration.source_system AS source
                  ON source.id = appeal.source_system_id AND source.region_id = appeal.region_id
                WHERE a.region_id = %s
                  AND a.assigned_at >= %s AND a.assigned_at < %s
                  AND source.system_code = ANY(%s)
                  AND COALESCE(appeal.legal_basis, '') <> 'SYNTHETIC_TEST_ONLY'
            ), outcome_first AS (
                SELECT o.assignment_id, min(o.observed_at) AS first_observed_at
                FROM ownership.handoff_outcome AS o
                JOIN cohort AS c ON c.assignment_id = o.assignment_id
                WHERE o.region_id = %s AND o.observed_at < %s
                GROUP BY o.assignment_id
            ), first_outcomes AS (
                SELECT o.assignment_id,
                       count(DISTINCT o.disposition) AS first_disposition_count,
                       min(o.disposition) AS first_disposition
                FROM ownership.handoff_outcome AS o
                JOIN outcome_first AS f
                  ON f.assignment_id = o.assignment_id AND f.first_observed_at = o.observed_at
                WHERE o.region_id = %s
                GROUP BY o.assignment_id
            ), identity_candidates AS (
                SELECT c.assignment_id, organization.organization_id
                FROM cohort AS c
                JOIN ownership.organization_version AS organization
                  ON organization.region_id = c.region_id
                 AND organization.organization_id = c.assignee_unit_id
                 AND organization.state = 'approved'
                 AND organization.synthetic_only = false
                 AND organization.effective_from <= c.assigned_at
                 AND (organization.effective_to IS NULL
                      OR c.assigned_at < organization.effective_to)
                UNION
                SELECT c.assignment_id, organization.organization_id
                FROM cohort AS c
                JOIN ownership.unit_organization_mapping AS m
                  ON m.region_id = c.region_id AND m.service_id = c.to_service_id
                 AND m.unit_id = c.assignee_unit_id AND m.state = 'approved'
                 AND m.synthetic_only = false AND m.effective_from <= c.assigned_at
                 AND (m.effective_to IS NULL OR c.assigned_at < m.effective_to)
                JOIN ownership.organization_version AS organization
                  ON organization.region_id = m.region_id
                 AND organization.organization_id = m.organization_id
                 AND organization.version = m.organization_version
                 AND organization.state = 'approved'
                 AND organization.synthetic_only = false
                 AND organization.effective_from <= c.assigned_at
                 AND (organization.effective_to IS NULL
                      OR c.assigned_at < organization.effective_to)
            ), resolved_identity AS (
                SELECT assignment_id,
                       CASE WHEN count(DISTINCT organization_id) = 1
                            THEN min(organization_id) END AS organization_id
                FROM identity_candidates
                GROUP BY assignment_id
            ), mapped AS (
                SELECT c.*, resolved.organization_id
                FROM cohort AS c
                LEFT JOIN resolved_identity AS resolved USING (assignment_id)
            ), repeat_flags AS (
                SELECT current.assignment_id,
                       EXISTS (
                           SELECT 1
                           FROM ownership.handoff_outcome AS prior
                           JOIN appeals.assignment AS prior_assignment
                             ON prior_assignment.assignment_id = prior.assignment_id
                           WHERE prior.region_id = %s
                             AND prior.request_id = current.request_id
                             AND prior.disposition = 'rejected'
                             AND prior.organization_id = current.organization_id
                             AND prior_assignment.new_version < current.new_version
                             AND prior.observed_at <= current.assigned_at
                       ) AS was_previously_rejected
                FROM mapped AS current
                WHERE current.organization_id IS NOT NULL
            )
            SELECT count(*) AS assignment_count,
                   count(*) FILTER (WHERE mapped.is_first_assignment
                       AND first.first_disposition_count = 1)
                       AS first_pass_denominator,
                   count(*) FILTER (WHERE mapped.is_first_assignment
                       AND first.first_disposition_count = 1
                       AND first.first_disposition = 'accepted') AS first_pass_accepted,
                   count(*) FILTER (WHERE mapped.is_first_assignment
                       AND (first.assignment_id IS NULL
                       OR first.first_disposition_count <> 1)) AS unclassified,
                   count(*) FILTER (WHERE mapped.organization_id IS NOT NULL)
                       AS repeated_denominator,
                   count(*) FILTER (WHERE mapped.organization_id IS NOT NULL
                       AND repeat.was_previously_rejected) AS repeated_numerator,
                   count(*) FILTER (WHERE mapped.organization_id IS NULL) AS unmapped
            FROM mapped
            LEFT JOIN first_outcomes AS first USING (assignment_id)
            LEFT JOIN repeat_flags AS repeat USING (assignment_id)
        """
        params: tuple[object, ...] = (
            query.region_id,
            query.start_at,
            query.end_at,
            codes,
            query.region_id,
            query.end_at,
            query.region_id,
            query.region_id,
        )
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
        assert row is not None
        return HandoffMetrics(
            region_id=query.region_id,
            interval_start=query.start_at,
            interval_end=query.end_at,
            assignment_count=row["assignment_count"],
            first_pass_acceptance=HandoffRate(
                numerator=row["first_pass_accepted"],
                denominator=row["first_pass_denominator"],
                numerator_definition=(
                    "The globally first assignment for an appeal whose earliest observed "
                    "outcome before interval_end is accepted"
                ),
                denominator_definition=(
                    "Appeals whose globally first assignment has an unambiguous earliest "
                    "observed outcome before interval_end; missing outcomes and conflicting "
                    "timestamp ties are excluded"
                ),
            ),
            first_pass_unclassified_assignments=row["unclassified"],
            repeated_rejected_handoffs=HandoffRate(
                numerator=row["repeated_numerator"],
                denominator=row["repeated_denominator"],
                numerator_definition=(
                    "Mapped assignments whose organization had a rejected outcome on an earlier "
                    "assignment for the same request before this assignment time"
                ),
                denominator_definition=(
                    "Assignments with one unambiguous approved, effective, non-synthetic "
                    "direct organization identity or unit-to-organization mapping at assigned_at"
                ),
            ),
            unmapped_assignments=row["unmapped"],
            provenance=(
                "appeals.assignment.assigned_at cohort; ownership.handoff_outcome.observed_at "
                "first observation before interval_end; approved effective non-synthetic "
                "direct or mapped organization identity; "
                "operational source allowlist"
            ),
            quality_state=(
                "no_data"
                if row["assignment_count"] == 0
                else "partial"
                if row["unclassified"] or row["unmapped"]
                else "complete"
            ),
        )
