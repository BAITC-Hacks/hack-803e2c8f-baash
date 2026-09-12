"""Transactional PostgreSQL sink for validated M1 import results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from .pipeline import MAPPING_VERSION, PARSER_VERSION, SCHEMA_VERSION, ImportResult


@dataclass(frozen=True)
class PersistenceReceipt:
    import_run_id: UUID
    replay: bool
    accepted: int
    quarantined: int


def _psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def _required_row(row: dict[str, Any] | None, operation: str) -> dict[str, Any]:
    if row is None:
        raise RuntimeError(f"database did not return a row for {operation}")
    return row


def persist_import_result(
    result: ImportResult,
    *,
    manifest: dict[str, Any],
    database_url: str,
    schema_sha256: str,
    source_file_ref: str,
) -> PersistenceReceipt:
    """Persist provenance and canonical rows atomically; exact batch replay is a no-op."""

    registry_region = str(manifest.get("source_registry_region", "MULTI"))
    adapter_version = str(manifest["adapter_version"])
    with psycopg.connect(_psycopg_url(database_url), row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO integration.source_system
                    (system_code, display_name, region_id, adapter_id, adapter_version)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (system_code) DO UPDATE SET
                    adapter_version = EXCLUDED.adapter_version,
                    updated_at = now()
                RETURNING id
                """,
                (
                    result.source_system,
                    f"Synthetic source {result.source_system}",
                    registry_region,
                    result.source_system,
                    adapter_version,
                ),
            )
            source_system_id = _required_row(cursor.fetchone(), "source system upsert")["id"]
            cursor.execute(
                """
                SELECT id FROM integration.import_run
                WHERE source_system_id = %s AND source_checksum = %s
                """,
                (source_system_id, result.batch_checksum),
            )
            replay = cursor.fetchone()
            if replay:
                return PersistenceReceipt(
                    replay["id"], True, len(result.accepted), len(result.quarantine)
                )

            cursor.execute(
                """
                INSERT INTO integration.source_schema_version
                    (source_system_id, version, contract_version, mapping_version,
                     schema_hash, status, effective_from)
                VALUES (%s, %s, %s, %s, %s, 'approved', %s)
                ON CONFLICT (source_system_id, version) DO NOTHING
                RETURNING id, schema_hash, mapping_version
                """,
                (
                    source_system_id,
                    adapter_version,
                    SCHEMA_VERSION,
                    MAPPING_VERSION,
                    schema_sha256,
                    result.observed_at,
                ),
            )
            source_schema = cursor.fetchone()
            if source_schema is None:
                cursor.execute(
                    """
                    SELECT id, schema_hash, mapping_version
                    FROM integration.source_schema_version
                    WHERE source_system_id = %s AND version = %s
                    """,
                    (source_system_id, adapter_version),
                )
                source_schema = _required_row(cursor.fetchone(), "source schema lookup")
            if (
                source_schema["schema_hash"] != schema_sha256
                or source_schema["mapping_version"] != MAPPING_VERSION
            ):
                raise ValueError("source schema version conflicts with immutable provenance")
            source_schema_version_id = source_schema["id"]
            report = result.report()
            cursor.execute(
                """
                INSERT INTO integration.import_run
                    (source_system_id, region_id, export_id, source_file_ref, source_checksum,
                     parser_version, mapping_version, row_count, accepted_count, warning_count,
                     quarantined_count, duplicate_count, data_cutoff, observed_at, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'received')
                RETURNING id
                """,
                (
                    source_system_id,
                    registry_region,
                    result.run_id,
                    source_file_ref,
                    result.batch_checksum,
                    PARSER_VERSION,
                    MAPPING_VERSION,
                    result.input_count,
                    len(result.accepted),
                    result.warning_count,
                    len(result.quarantine),
                    result.duplicate_count,
                    result.observed_at,
                    result.observed_at,
                ),
            )
            import_run_id = _required_row(cursor.fetchone(), "import run insert")["id"]

            for canonical in result.accepted:
                source = canonical["source"]
                ingestion = canonical["ingestion"]
                timing = canonical["time"]
                cursor.execute(
                    """
                    INSERT INTO integration.source_record
                        (import_run_id, source_system_id, source_schema_version_id,
                         source_request_id, source_row_ref, raw_payload_ref, raw_payload_hash,
                         canonical_payload, validation_status, occurred_at, observed_at,
                         source_timezone, time_quality)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_system_id, source_request_id) DO NOTHING
                    RETURNING id
                    """,
                    (
                        import_run_id,
                        source_system_id,
                        source_schema_version_id,
                        source["request_id"],
                        f"{result.source_system}:{source['request_id']}",
                        ingestion["raw_payload_ref"],
                        source["source_record_checksum"],
                        json.dumps(canonical, ensure_ascii=True, sort_keys=True),
                        ingestion["validation_status"],
                        timing["received_at"],
                        timing["observed_at"],
                        timing["source_timezone"],
                        timing["received_at_quality"],
                    ),
                )
                inserted = cursor.fetchone()
                if inserted:
                    source_record_id = inserted["id"]
                else:
                    cursor.execute(
                        """
                        SELECT id, raw_payload_hash FROM integration.source_record
                        WHERE source_system_id = %s AND source_request_id = %s
                        """,
                        (source_system_id, source["request_id"]),
                    )
                    existing = _required_row(cursor.fetchone(), "source identity lookup")
                    if existing["raw_payload_hash"] != source["source_record_checksum"]:
                        raise ValueError(
                            f"conflicting persisted source identity: {source['request_id']}"
                        )
                    source_record_id = existing["id"]

                intake = canonical["intake"]
                governance = canonical["governance"]
                location = canonical["location"]
                appeal_status = canonical.get("execution", {}).get("current_status", "new")
                cursor.execute(
                    """
                    INSERT INTO appeals.appeal
                        (request_id, source_record_id, source_system_id, source_request_id,
                         region_id, channel, language, status, occurred_at, observed_at,
                         source_timezone, time_quality, citizen_token, raw_text_ref,
                         transcript_ref, geo_id, object_id, precision_m, normalization_status,
                         legal_basis, retention_class, redaction_version, deletion_due_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (request_id) DO NOTHING
                    """,
                    (
                        canonical["request_id"],
                        source_record_id,
                        source_system_id,
                        source["request_id"],
                        source["region_id"],
                        intake["channel"],
                        intake["language"],
                        appeal_status,
                        timing["received_at"],
                        timing["observed_at"],
                        timing["source_timezone"],
                        timing["received_at_quality"],
                        intake["citizen_token"],
                        intake["raw_text_ref"],
                        intake["transcript_ref"],
                        location["geo_id"],
                        location["object_id"],
                        location["precision_m"],
                        location["normalization_status"],
                        governance["legal_basis"],
                        governance["retention_class"],
                        governance["redaction_version"],
                        governance["deletion_due_at"],
                    ),
                )

            for item in result.quarantine:
                cursor.execute(
                    """
                    INSERT INTO integration.quarantine_record
                        (import_run_id, source_system_id, source_row_ref, raw_payload_ref,
                         raw_payload_hash, error_code, error_detail)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        import_run_id,
                        source_system_id,
                        item.source_row_ref,
                        item.raw_payload_ref,
                        item.raw_hash,
                        item.error_code,
                        item.message,
                    ),
                )
            cursor.execute(
                "UPDATE integration.import_run SET status = 'completed' WHERE id = %s",
                (import_run_id,),
            )
            assert report["accepted"] == len(result.accepted)
        connection.commit()
    return PersistenceReceipt(import_run_id, False, len(result.accepted), len(result.quarantine))
