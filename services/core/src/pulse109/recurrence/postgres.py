"""Region-scoped read model for confirmed incidents with verified closure."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from .models import PriorVerifiedIncident, RecurrenceContext
from .service import RecurrenceError


class PostgresRecurrenceRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def context(self, request_id: UUID, *, region_id: str) -> RecurrenceContext:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT a.request_id, a.version AS request_version, a.region_id,
                              a.object_id, a.occurred_at, a.time_quality,
                              (SELECT d.topic_id FROM triage.operator_decision AS d
                               WHERE d.request_id = a.request_id
                               ORDER BY d.decided_at DESC, d.decision_id DESC LIMIT 1) AS topic_id
                       FROM appeals.appeal AS a
                       WHERE a.request_id = %s AND a.region_id = %s""",
                    (request_id, region_id),
                )
                row = cursor.fetchone()
        if row is None:
            raise RecurrenceError(
                "appeal_not_found", "The appeal is not available in this region.", 404
            )
        return RecurrenceContext.model_validate(row)

    def prior_verified_incidents(
        self,
        *,
        request_id: UUID,
        region_id: str,
        object_id: str,
        topic_id: str,
        occurred_at: datetime,
        window_days: int,
    ) -> list[PriorVerifiedIncident]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """WITH latest_membership AS (
                           SELECT DISTINCT ON (m.incident_id, m.request_id)
                                  m.incident_id, m.request_id, m.decision
                           FROM incidents.membership_decision AS m
                           JOIN incidents.incident AS i ON i.incident_id = m.incident_id
                           WHERE i.region_id = %s AND i.topic_id = %s
                           ORDER BY m.incident_id, m.request_id,
                                    m.decided_at DESC, m.membership_decision_id DESC
                       )
                       SELECT i.incident_id,
                              min(a.occurred_at) AS first_reported_at,
                              max(c.confirmed_at) AS last_verified_closure_at,
                              count(DISTINCT a.request_id) AS supporting_appeal_count
                       FROM incidents.incident AS i
                       JOIN latest_membership AS m ON m.incident_id = i.incident_id
                       JOIN appeals.appeal AS a ON a.request_id = m.request_id
                       JOIN appeals.closure_preflight AS c ON c.request_id = a.request_id
                       WHERE i.region_id = %s AND i.topic_id = %s
                         AND i.state IN ('confirmed', 'monitoring', 'resolved', 'closed')
                         AND m.decision = 'confirm'
                         AND a.region_id = %s AND a.object_id = %s
                         AND a.time_quality = 'exact' AND a.occurred_at IS NOT NULL
                         AND c.confirmed_at IS NOT NULL
                         AND a.request_id <> %s
                         AND NOT EXISTS (
                             SELECT 1 FROM incidents.incident_candidate_member AS cm
                             WHERE cm.incident_id = i.incident_id AND cm.request_id = %s
                         )
                       GROUP BY i.incident_id
                       HAVING max(c.confirmed_at) < %s
                          AND max(c.confirmed_at) >= %s
                       ORDER BY last_verified_closure_at DESC, i.incident_id DESC""",
                    (
                        region_id,
                        topic_id,
                        region_id,
                        topic_id,
                        region_id,
                        object_id,
                        request_id,
                        request_id,
                        occurred_at,
                        occurred_at - timedelta(days=window_days),
                    ),
                )
                rows = cursor.fetchall()
        return [PriorVerifiedIncident.model_validate(row) for row in rows]
