"""PostgreSQL integration test for incident topology persistence."""

import os
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest
from pulse109.incidents.models import (
    CreateIncident,
    IncidentDecision,
    IncidentMergeCommand,
    IncidentSplitCommand,
    MembershipCommand,
)
from pulse109.incidents.postgres import PostgresIncidentService
from pulse109.manual_path import PostgresManualPathService, PostgresManualRepository
from pulse109.manual_path.models import CreateRequest


class DummyConnectionPool:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def connection(self):
        return psycopg.connect(self._dsn, autocommit=False)


@pytest.mark.integration
def test_postgres_incident_merge_and_split_topology() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    dsn = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    pool = DummyConnectionPool(dsn)
    service = PostgresIncidentService(pool)
    region_id = "ALA"
    actor = "synthetic-supervisor"

    # Seed appeals through the manual path service rather than raw SQL. An
    # appeal requires a whole chain of foreign keys, source_system to
    # import_run to source_record, and the service is what creates it. The
    # previous direct INSERT omitted the NOT NULL source_record_id and also
    # used column and status names that do not exist in the schema.
    manual = PostgresManualPathService(PostgresManualRepository(database_url))
    appeal_ids: list[str] = []
    for _idx in range(4):
        source_id = f"TOPOLOGY-{uuid4()}"
        appeal, _replayed = manual.create(
            CreateRequest(
                source_system="synthetic-topology-integration",
                source_request_id=source_id,
                region_id=region_id,
                received_at=datetime.now(timezone.utc),
                received_at_quality="exact",
                channel="web",
                language="ru",
                text="Synthetic appeal seeded for incident topology test",
                consent_or_legal_basis="SYNTHETIC_TEST_ONLY",
            ),
            idempotency_key=f"create-{source_id}",
            region_id=region_id,
            actor=actor,
            correlation_id=f"correlation-{source_id}",
        )
        appeal_ids.append(str(appeal.request_id))

    # Create Incident A with appeals 0 and 1
    inc_a, _ = service.create(
        CreateIncident(
            region_id=region_id,
            topic_id="topic:water",
            service_id="service:water",
            member_request_ids=[appeal_ids[0], appeal_ids[1]],
            proposal_source="operator",
        ),
        idempotency_key=f"top-create-a-{uuid4()}",
        region_id=region_id,
        actor=actor,
        correlation_id=f"corr-{uuid4()}",
    )

    # Confirm members in Incident A
    for idx, aid in enumerate([appeal_ids[0], appeal_ids[1]], start=1):
        service.decide_member(
            inc_a.incident_id,
            MembershipCommand(
                request_id=aid,
                incident_version=idx,
                decision="confirm",
                reason_code="VERIFIED_MEMBER",
            ),
            idempotency_key=f"top-mem-a-{idx}-{uuid4()}",
            region_id=region_id,
            actor=actor,
            correlation_id=f"corr-mem-{idx}",
        )

    # Confirm Incident A
    inc_a_confirmed = service.decide_incident(
        inc_a.incident_id,
        IncidentDecision(
            incident_version=3,
            decision="confirm",
            reason_code="ALL_CONFIRMED",
        ),
        idempotency_key=f"top-conf-a-{uuid4()}",
        region_id=region_id,
        actor=actor,
        correlation_id="corr-conf-a",
    )
    assert inc_a_confirmed.state == "confirmed"
    assert inc_a_confirmed.version == 4

    # Create Incident B with appeals 2 and 3
    inc_b, _ = service.create(
        CreateIncident(
            region_id=region_id,
            topic_id="topic:water",
            service_id="service:water",
            member_request_ids=[appeal_ids[2], appeal_ids[3]],
            proposal_source="operator",
        ),
        idempotency_key=f"top-create-b-{uuid4()}",
        region_id=region_id,
        actor=actor,
        correlation_id=f"corr-{uuid4()}",
    )

    for idx, aid in enumerate([appeal_ids[2], appeal_ids[3]], start=1):
        service.decide_member(
            inc_b.incident_id,
            MembershipCommand(
                request_id=aid,
                incident_version=idx,
                decision="confirm",
                reason_code="VERIFIED_MEMBER",
            ),
            idempotency_key=f"top-mem-b-{idx}-{uuid4()}",
            region_id=region_id,
            actor=actor,
            correlation_id=f"corr-mem-b-{idx}",
        )

    inc_b_confirmed = service.decide_incident(
        inc_b.incident_id,
        IncidentDecision(
            incident_version=3,
            decision="confirm",
            reason_code="ALL_CONFIRMED",
        ),
        idempotency_key=f"top-conf-b-{uuid4()}",
        region_id=region_id,
        actor=actor,
        correlation_id="corr-conf-b",
    )
    assert inc_b_confirmed.state == "confirmed"
    assert inc_b_confirmed.version == 4

    # Merge Incident A into Incident B
    merge_key = f"top-merge-{uuid4()}"
    merged = service.merge(
        inc_a.incident_id,
        IncidentMergeCommand(
            target_incident_id=inc_b.incident_id,
            source_version=inc_a_confirmed.version,
            target_version=inc_b_confirmed.version,
            member_request_ids=[appeal_ids[0], appeal_ids[1]],
            reason_code="MERGE_INCIDENT_AREAS",
            evidence_refs=["e" * 64],
        ),
        idempotency_key=merge_key,
        region_id=region_id,
        actor=actor,
        correlation_id=f"corr-merge-{uuid4()}",
    )
    assert merged["operation"] == "merge"
    assert merged["source"]["state"] == "superseded"
    assert merged["target"]["member_count"] == 4

    # Verify relation decision in database
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT operation, source_incident_id, target_incident_id, reason_code
            FROM incidents.incident_relation_decision
            WHERE source_incident_id = %s AND target_incident_id = %s
            """,
            (inc_a.incident_id, inc_b.incident_id),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "merge"
        assert row[3] == "MERGE_INCIDENT_AREAS"

    # Test Split from Incident B (now having 4 members: 0, 1, 2, 3)
    split_key = f"top-split-{uuid4()}"
    split = service.split(
        inc_b.incident_id,
        IncidentSplitCommand(
            source_version=merged["target"]["version"],
            member_request_ids=[appeal_ids[0], appeal_ids[1]],
            reason_code="SPLIT_DISTRICT_CLUSTER",
            evidence_refs=["f" * 64],
        ),
        idempotency_key=split_key,
        region_id=region_id,
        actor=actor,
        correlation_id=f"corr-split-{uuid4()}",
    )
    assert split["operation"] == "split"
    assert split["source"]["member_count"] == 2
    assert split["target"]["state"] == "proposed"
    assert split["target"]["version"] == 1
