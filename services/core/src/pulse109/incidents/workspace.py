"""Assemble the incident war room in one read.

The frontend used to need a request per panel to show one incident. That is slow
and it invites panels to disagree with each other, because each one sees a
different instant. This service reads the whole situation inside a single
connection and returns it as one consistent snapshot.

It composes rather than computes. Ownership, outcome memory and next actions stay
in their own modules and are injected. Whatever is missing reports as
UNAVAILABLE instead of returning an empty list that reads like an answer.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any, Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from pulse109.capability import CapabilityStatus

from .models import IncidentDetail
from .service import IncidentError
from .workspace_models import (
    GeoFootprint,
    IncidentWorkspace,
    NextActionSummary,
    OwnershipSummary,
    RecurrenceSummary,
    SimilarOutcome,
    SimilarOutcomes,
    SynchronizationSummary,
    WorkspaceEvidence,
    WorkspaceMember,
    WorkspacePoint,
    WorkspaceTimelineEntry,
)

_LOGGER = logging.getLogger(__name__)
_EARTH_RADIUS_M = 6_371_000.0
_MAX_MEMBERS = 500


class OwnershipAdvisor(Protocol):
    """Ownership assessment for the incident's leading appeal."""

    def assess_request(self, request_id: UUID, *, region_id: str) -> dict[str, Any]: ...


class OutcomeAdvisor(Protocol):
    """Verified, human-closed outcomes comparable to this incident."""

    def comparable(
        self,
        *,
        region_id: str,
        topic_id: str,
        service_id: str | None,
        leading_request_id: UUID | None,
    ) -> list[dict[str, Any]]: ...


class NextActionAdvisor(Protocol):
    """Evidence-backed suggestions. Never an instruction, never a command."""

    def suggest(self, workspace: IncidentWorkspace) -> list[dict[str, Any]]: ...


def _psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def _haversine_m(first: WorkspacePoint, second: WorkspacePoint) -> float:
    lat1, lat2 = math.radians(first.latitude), math.radians(second.latitude)
    delta_lat = lat2 - lat1
    delta_lon = math.radians(second.longitude - first.longitude)
    inner = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(inner))


def build_footprint(members: Sequence[WorkspaceMember]) -> GeoFootprint:
    """Describe where the reports fall, and say so when nothing is located.

    No regional export in this programme carries coordinates, so an absent
    footprint is the normal case rather than a defect. Reporting it as
    UNAVAILABLE keeps an operator from reading an empty map as "no spread".
    """
    points = [member.point for member in members if member.point is not None]
    if not points:
        return GeoFootprint(
            status=CapabilityStatus.unavailable("COORDINATES_ABSENT"),
            located_member_count=0,
            total_member_count=len(members),
        )
    if len(points) == 1:
        only = points[0]
        return GeoFootprint(
            status=CapabilityStatus.abstained("SINGLE_LOCATED_REPORT"),
            located_member_count=1,
            total_member_count=len(members),
            centroid=only,
            report_spread_m=0.0,
            bounding_box=(only.longitude, only.latitude, only.longitude, only.latitude),
            points=[only],
        )
    centroid = WorkspacePoint(
        longitude=sum(point.longitude for point in points) / len(points),
        latitude=sum(point.latitude for point in points) / len(points),
    )
    spread = max(_haversine_m(centroid, point) for point in points)
    return GeoFootprint(
        status=CapabilityStatus.available(),
        located_member_count=len(points),
        total_member_count=len(members),
        centroid=centroid,
        report_spread_m=round(spread, 1),
        bounding_box=(
            min(point.longitude for point in points),
            min(point.latitude for point in points),
            max(point.longitude for point in points),
            max(point.latitude for point in points),
        ),
        points=points,
    )


def _median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


class PostgresIncidentWorkspaceService:
    """One consistent snapshot of one incident."""

    def __init__(
        self,
        database_url: str,
        *,
        detail_reader: Any,
        ownership: OwnershipAdvisor | None = None,
        outcomes: OutcomeAdvisor | None = None,
        next_actions: NextActionAdvisor | None = None,
        synthetic: bool = False,
    ) -> None:
        self.database_url = database_url
        self._detail_reader = detail_reader
        self._ownership = ownership
        self._outcomes = outcomes
        self._next_actions = next_actions
        self._synthetic = synthetic

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(_psycopg_url(self.database_url), row_factory=dict_row) as connection:
            yield connection

    def workspace(self, incident_id: UUID, *, region_id: str) -> IncidentWorkspace:
        detail: IncidentDetail = self._detail_reader.detail(incident_id, region_id=region_id)
        confirmed = list(detail.confirmed_member_request_ids)[:_MAX_MEMBERS]
        candidates = [
            request_id
            for request_id in detail.candidate_member_request_ids
            if request_id not in set(confirmed)
        ][: max(0, _MAX_MEMBERS - len(confirmed))]

        with self._connection() as connection, connection.cursor() as cursor:
            members = self._read_members(cursor, confirmed, candidates, region_id)
            timeline = self._read_timeline(cursor, [member.request_id for member in members])
            evidence = self._read_evidence(cursor, [member.request_id for member in members])
            synchronization = self._read_sync(cursor, [member.request_id for member in members])

        reported = [member.received_at for member in members if member.received_at is not None]
        first_reported = min(reported) if reported else None
        last_reported = max(reported) if reported else None
        active_minutes = (
            round((last_reported - first_reported).total_seconds() / 60, 1)
            if first_reported and last_reported
            else None
        )

        workspace = IncidentWorkspace(
            incident_id=detail.incident_id,
            region_id=detail.region_id,
            state=detail.state,
            topic_id=detail.topic_id,
            service_id=detail.service_id,
            version=detail.version,
            member_count=detail.member_count,
            confirmed_count=len(confirmed),
            candidate_count=len(candidates),
            first_reported_at=first_reported,
            last_reported_at=last_reported,
            active_minutes=active_minutes,
            members=members,
            geo=build_footprint(members),
            ownership=self._assess_ownership(members, region_id),
            similar_outcomes=self._comparable_outcomes(detail, members),
            next_actions=NextActionSummary(
                status=CapabilityStatus.unavailable("NEXT_ACTION_NOT_CONFIGURED")
            ),
            recurrence=RecurrenceSummary(
                status=CapabilityStatus.unavailable("RECURRENCE_NOT_CONFIGURED")
            ),
            synchronization=synchronization,
            timeline=timeline,
            evidence=evidence,
            synthetic=self._synthetic,
        )
        return workspace.model_copy(update={"next_actions": self._suggest(workspace)})

    # ------------------------------------------------------------------
    # storage reads
    # ------------------------------------------------------------------

    def _read_members(
        self,
        cursor: psycopg.Cursor[dict[str, Any]],
        confirmed: Sequence[UUID],
        candidates: Sequence[UUID],
        region_id: str,
    ) -> list[WorkspaceMember]:
        request_ids = [*confirmed, *candidates]
        if not request_ids:
            return []
        cursor.execute(
            """
            SELECT request_id, source_request_id, status, received_at, received_at_quality,
                   language, channel, precision_m,
                   ST_X(location::geometry) AS longitude,
                   ST_Y(location::geometry) AS latitude
            FROM appeals.appeal
            WHERE request_id = ANY(%s) AND region_id = %s
            """,
            ([str(request_id) for request_id in request_ids], region_id),
        )
        confirmed_set = set(confirmed)
        by_id: dict[UUID, WorkspaceMember] = {}
        for row in cursor.fetchall():
            request_id = UUID(str(row["request_id"]))
            point = None
            if row["longitude"] is not None and row["latitude"] is not None:
                point = WorkspacePoint(
                    longitude=float(row["longitude"]),
                    latitude=float(row["latitude"]),
                    precision_m=(
                        float(row["precision_m"]) if row["precision_m"] is not None else None
                    ),
                )
            by_id[request_id] = WorkspaceMember(
                request_id=request_id,
                source_request_id=row["source_request_id"],
                membership="confirmed" if request_id in confirmed_set else "candidate",
                status=row["status"],
                received_at=row["received_at"],
                received_at_quality=row["received_at_quality"],
                language=row["language"],
                channel=row["channel"],
                point=point,
            )
        # Preserve the caller's ordering: confirmed members first.
        return [by_id[request_id] for request_id in request_ids if request_id in by_id]

    def _read_timeline(
        self, cursor: psycopg.Cursor[dict[str, Any]], request_ids: Sequence[UUID]
    ) -> list[WorkspaceTimelineEntry]:
        if not request_ids:
            return []
        cursor.execute(
            """
            SELECT event_type, actor_type, COALESCE(occurred_at, observed_at) AS at
            FROM appeals.appeal_event
            WHERE appeal_id = ANY(%s)
            ORDER BY COALESCE(occurred_at, observed_at) ASC
            LIMIT 200
            """,
            ([str(request_id) for request_id in request_ids],),
        )
        return [
            WorkspaceTimelineEntry(
                occurred_at=row["at"],
                event_type=row["event_type"],
                actor_type=row["actor_type"],
                summary_code=row["event_type"].upper().replace(".", "_"),
            )
            for row in cursor.fetchall()
            if row["at"] is not None
        ]

    def _read_evidence(
        self, cursor: psycopg.Cursor[dict[str, Any]], request_ids: Sequence[UUID]
    ) -> list[WorkspaceEvidence]:
        if not request_ids:
            return []
        cursor.execute(
            """
            SELECT appeal_id, object_hash, media_type, created_at
            FROM appeals.attachment_ref
            WHERE appeal_id = ANY(%s)
            ORDER BY created_at ASC
            LIMIT 100
            """,
            ([str(request_id) for request_id in request_ids],),
        )
        return [
            WorkspaceEvidence(
                evidence_ref=f"sha256:{row['object_hash']}",
                evidence_type=str(row["media_type"]).split("/")[0],
                owner_request_id=UUID(str(row["appeal_id"])),
                verified_at=row["created_at"],
            )
            for row in cursor.fetchall()
        ]

    def _read_sync(
        self, cursor: psycopg.Cursor[dict[str, Any]], request_ids: Sequence[UUID]
    ) -> SynchronizationSummary:
        if not request_ids:
            return SynchronizationSummary(
                status=CapabilityStatus.unavailable("NO_MEMBERS"),
                queued=0,
                delivered=0,
                retrying=0,
                failed_permanent=0,
            )
        cursor.execute(
            """
            SELECT status, count(*) AS total
            FROM integration.outbox
            WHERE subject_id = ANY(%s)
            GROUP BY status
            """,
            ([str(request_id) for request_id in request_ids],),
        )
        counts = {row["status"]: int(row["total"]) for row in cursor.fetchall()}
        return SynchronizationSummary(
            status=CapabilityStatus.available(),
            queued=counts.get("pending", 0) + counts.get("processing", 0),
            delivered=counts.get("published", 0),
            retrying=counts.get("retrying", 0),
            failed_permanent=counts.get("dead_letter", 0),
        )

    # ------------------------------------------------------------------
    # injected advisors
    # ------------------------------------------------------------------

    def _assess_ownership(
        self, members: Sequence[WorkspaceMember], region_id: str
    ) -> OwnershipSummary:
        if self._ownership is None:
            return OwnershipSummary(status=CapabilityStatus.unavailable("OWNERSHIP_NOT_CONFIGURED"))
        leading = next((member for member in members if member.membership == "confirmed"), None)
        if leading is None:
            return OwnershipSummary(status=CapabilityStatus.abstained("NO_CONFIRMED_MEMBER"))
        try:
            assessment = self._ownership.assess_request(leading.request_id, region_id=region_id)
        except Exception:
            _LOGGER.warning("ownership assessment unavailable", exc_info=True)
            return OwnershipSummary(status=CapabilityStatus.unavailable("OWNERSHIP_READ_FAILED"))
        candidates = list(assessment.get("candidates") or [])
        if not candidates:
            return OwnershipSummary(
                status=CapabilityStatus.abstained("NO_OWNERSHIP_CANDIDATE"),
                reason_codes=list(assessment.get("reason_codes") or []),
            )
        return OwnershipSummary(
            status=CapabilityStatus.available(),
            candidates=candidates[:10],
            ambiguous=bool(assessment.get("ambiguous")),
            loop_risk=bool(assessment.get("loop_risk")),
            reason_codes=list(assessment.get("reason_codes") or [])[:20],
        )

    def _comparable_outcomes(
        self, detail: IncidentDetail, members: Sequence[WorkspaceMember]
    ) -> SimilarOutcomes:
        if self._outcomes is None:
            return SimilarOutcomes(
                status=CapabilityStatus.unavailable("OUTCOME_MEMORY_NOT_CONFIGURED"),
                comparable_count=0,
            )
        try:
            leading = next(
                (member for member in members if member.membership == "confirmed"),
                members[0] if members else None,
            )
            rows = self._outcomes.comparable(
                region_id=detail.region_id,
                topic_id=detail.topic_id,
                service_id=detail.service_id,
                leading_request_id=leading.request_id if leading else None,
            )
        except Exception:
            _LOGGER.warning("outcome memory unavailable", exc_info=True)
            return SimilarOutcomes(
                status=CapabilityStatus.unavailable("OUTCOME_MEMORY_READ_FAILED"),
                comparable_count=0,
            )
        if not rows:
            return SimilarOutcomes(
                status=CapabilityStatus.abstained("NO_COMPARABLE_VERIFIED_OUTCOME"),
                comparable_count=0,
            )
        items = [SimilarOutcome(**row) for row in rows[:20]]
        durations = [item.resolution_hours for item in items if item.resolution_hours is not None]
        without_recurrence = sum(1 for item in items if item.recurred_within_30d is False)
        return SimilarOutcomes(
            status=CapabilityStatus.available(),
            comparable_count=len(rows),
            median_resolution_hours=_median(durations),
            without_recurrence_30d=without_recurrence,
            items=items,
        )

    def _suggest(self, workspace: IncidentWorkspace) -> NextActionSummary:
        if self._next_actions is None:
            return NextActionSummary(
                status=CapabilityStatus.unavailable("NEXT_ACTION_NOT_CONFIGURED")
            )
        try:
            items = self._next_actions.suggest(workspace)
        except Exception:
            _LOGGER.warning("next action advisor unavailable", exc_info=True)
            return NextActionSummary(status=CapabilityStatus.unavailable("NEXT_ACTION_FAILED"))
        if not items:
            return NextActionSummary(status=CapabilityStatus.abstained("NO_SUPPORTED_ACTION"))
        return NextActionSummary(status=CapabilityStatus.available(), items=items[:10])


__all__ = [
    "IncidentError",
    "PostgresIncidentWorkspaceService",
    "build_footprint",
]
