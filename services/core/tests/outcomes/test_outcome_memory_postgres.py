from datetime import datetime, timezone
from uuid import UUID

import pytest
from pulse109.outcome_memory.models import OutcomeMemoryQuery
from pulse109.outcome_memory.postgres import OutcomeCorpusUnavailable, PostgresOutcomeMemoryReader


class Cursor:
    def __init__(self, row):
        self.row = row
        self.sql = ""
        self.params = ()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        self.sql, self.params = sql, params

    def fetchone(self):
        return self.row


class Connection:
    def __init__(self, cursor):
        self.cursor_value = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return self.cursor_value


def test_inspection_queries_one_region_scoped_appeal_without_payload_text(monkeypatch):
    cursor = Cursor(None)
    monkeypatch.setattr(
        "pulse109.outcome_memory.postgres.psycopg.connect",
        lambda *_args, **_kwargs: Connection(cursor),
    )
    request_id = UUID("10000000-0000-0000-0000-000000000001")
    reader = PostgresOutcomeMemoryReader("postgresql://db", max_evidence=10)

    result = reader.inspect(request_id, "AST")

    assert result.reasons == ("closure_chain_missing",)
    assert cursor.params == (request_id, "AST")
    assert "LIMIT 1" in cursor.sql
    assert "raw_payload_hash" in cursor.sql
    assert "raw_payload_ref" not in cursor.sql
    assert "redacted_text" not in cursor.sql


def test_valid_available_chain_is_reported_but_missing_governance_blocks_candidate(monkeypatch):
    source_id = UUID(int=8)
    cursor = Cursor(
        {
            "preflight_id": UUID(int=1),
            "closure_id": UUID(int=2),
            "confirmed_at": "2026-09-25T08:00:00Z",
            "closure_event_id": UUID(int=3),
            "actor_id_token": "operator-token",
            "actor_type": "operator",
            "closure_confirmed_at": "2026-09-25T08:00:00Z",
            "operator_decision_at": "2026-09-25T07:00:00Z",
            "evidence_count": 1,
            "owned_evidence_count": 1,
            "source_schema_status": "approved",
            "source_schema_version": "regional.v1",
            "schema_source_system_id": source_id,
            "record_source_system_id": source_id,
            "import_source_system_id": source_id,
            "schema_effective_from": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "schema_effective_to": None,
            "source_observed_at": datetime(2026, 9, 1, tzinfo=timezone.utc),
            "validation_status": "accepted",
            "import_status": "completed",
            "import_region": "AST",
            "source_region": "AST",
            "redaction_version": "redaction.v1",
            "raw_payload_hash": "a" * 64,
        }
    )
    monkeypatch.setattr(
        "pulse109.outcome_memory.postgres.psycopg.connect",
        lambda *_args, **_kwargs: Connection(cursor),
    )
    request_id = UUID("10000000-0000-0000-0000-000000000001")
    reader = PostgresOutcomeMemoryReader("postgresql://db")

    result = reader.inspect(request_id, "AST")

    assert result.closure_chain_verified
    assert result.source_payload_hash == "a" * 64
    assert result.source_schema_version == "regional.v1"
    assert result.evidence_count == 1
    assert result.reasons == (
        "evidence_verification_time_missing",
        "evidence_verifier_provenance_missing",
        "approved_corpus_missing",
        "controlled_retrieval_terms_missing",
        "retention_approval_missing",
    )
    assert not result.candidate_ready


def test_reader_explicitly_reports_unavailable_corpus_even_with_synthetic_opt_in():
    query = OutcomeMemoryQuery(
        request_id=UUID("10000000-0000-0000-0000-000000000001"),
        region_id="AST",
        service_id="water.utility",
        topic_id="water.outage",
        terms=("drain",),
        allow_synthetic=True,
    )

    with pytest.raises(OutcomeCorpusUnavailable):
        PostgresOutcomeMemoryReader("postgresql://db").read_resolved_candidates(query)
