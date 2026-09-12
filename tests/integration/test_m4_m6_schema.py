import os

import psycopg
import pytest


@pytest.mark.integration
def test_m4_to_m6_tables_and_indexes_are_installed() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")
    url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    expected_tables = {
        "analytics.alert",
        "analytics.forecast",
        "analytics.metric_definition",
        "analytics.metric_result",
        "incidents.duplicate_candidate",
        "incidents.incident",
        "incidents.membership_decision",
        "integration.checkpoint",
        "integration.dead_letter",
        "integration.delivery_attempt",
        "integration.status_mapping",
        "reports.report_artifact",
        "reports.report_job",
        "triage.retrieval_document",
        "triage.retrieval_run",
    }
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT schemaname || '.' || tablename
            FROM pg_tables
            WHERE schemaname IN ('analytics', 'incidents', 'integration', 'reports', 'triage')
            """
        )
        installed = {str(row[0]) for row in cursor.fetchall()}
        assert expected_tables <= installed
        cursor.execute(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'triage' AND tablename = 'retrieval_document'
            """
        )
        indexes = {str(row[0]) for row in cursor.fetchall()}
        assert "retrieval_document_fts_idx" in indexes
        assert "retrieval_document_embedding_idx" in indexes


@pytest.mark.integration
def test_unknown_status_mapping_can_only_enter_review_without_canonical_status() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")
    url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO integration.source_system (
                system_code, display_name, region_id, adapter_id, adapter_version, active
            ) VALUES (
                'synthetic-m6-schema', 'Synthetic M6 Schema', 'ALA', 'replay', '1.0.0', true
            ) ON CONFLICT (system_code) DO NOTHING
            """
        )
        cursor.execute(
            """
            INSERT INTO integration.status_mapping (
                source_system_id, mapping_version, source_status, canonical_status,
                review_state, effective_from, synthetic_only
            ) VALUES (
                (
                    SELECT id FROM integration.source_system
                    WHERE system_code = 'synthetic-m6-schema'
                ),
                '1.0.0', 'UNRECOGNIZED', NULL,
                'mapping_review', '2026-09-12T00:00:00Z', true
            )
            RETURNING review_state, canonical_status
            """
        )
        assert cursor.fetchone() == ("mapping_review", None)
