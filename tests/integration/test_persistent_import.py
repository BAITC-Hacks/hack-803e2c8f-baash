import hashlib
import json
import os
from uuid import uuid4

import psycopg
import pytest
from pulse109.ingestion.pipeline import ingest_jsonl, load_schema
from pulse109.ingestion.postgres_store import persist_import_result


@pytest.mark.integration
def test_persistent_import_is_atomic_and_exact_replay_is_noop() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    nonce = uuid4().hex
    source_system = f"synthetic-{nonce[:12]}"
    row = {
        "access_scope": ["region:ALA", "purpose:test"],
        "channel": "web",
        "language": "mixed",
        "legal_basis": "SYNTHETIC_TEST_ONLY",
        "pii_flags": ["none"],
        "received_at": "2026-09-12T10:00:00+05:00",
        "region_id": "ALA",
        "retention_class": "synthetic-ephemeral",
        "source_request_id": f"REQ-{nonce}",
        "source_system": source_system,
        "status": "new",
    }
    schema_path = "contracts/canonical_request.schema.json"
    result = ingest_jsonl(
        [json.dumps(row)],
        source_system=source_system,
        run_id=f"run-{nonce}",
        observed_at="2026-09-12T12:00:00Z",
        schema=load_schema(schema_path),
        expected_regions=["ALA"],
    )
    manifest = {
        "adapter_version": "1.0.0",
        "source_registry_region": "ALA",
        "synthetic_only": True,
    }
    with open(schema_path, "rb") as schema_stream:
        schema_hash = hashlib.sha256(schema_stream.read()).hexdigest()

    first = persist_import_result(
        result,
        manifest=manifest,
        database_url=database_url,
        schema_sha256=schema_hash,
        source_file_ref="synthetic://integration-test",
    )
    second = persist_import_result(
        result,
        manifest=manifest,
        database_url=database_url,
        schema_sha256=schema_hash,
        source_file_ref="synthetic://integration-test",
    )

    assert first.replay is False
    assert second.replay is True
    assert first.import_run_id == second.import_run_id
    with psycopg.connect(database_url.replace("postgresql+psycopg://", "postgresql://", 1)) as db:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    (SELECT count(*) FROM integration.import_run WHERE id = %s),
                    (SELECT count(*) FROM integration.source_record WHERE import_run_id = %s),
                    (SELECT count(*) FROM appeals.appeal WHERE source_request_id = %s)
                """,
                (first.import_run_id, first.import_run_id, row["source_request_id"]),
            )
            assert cursor.fetchone() == (1, 1, 1)
