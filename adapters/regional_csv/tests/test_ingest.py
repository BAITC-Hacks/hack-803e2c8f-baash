from __future__ import annotations

import json
from io import StringIO

from pulse109_regional_csv.ingest import (
    REGIONS,
    _emit,
    parse_time,
    quarantine_entry,
    redact,
    to_canonical,
)


def test_naive_datetime_does_not_become_utc_instant() -> None:
    assert parse_time("2025-03-14 18:58:41", "iso") == (None, "missing")
    assert parse_time("14.03.2025 18:58:41", "dmy") == (None, "missing")
    assert parse_time("3/14/2025 18:58", "mdy") == (None, "missing")


def test_date_only_does_not_become_midnight_instant() -> None:
    assert parse_time("2025-03-14", "iso") == (None, "date_only")
    assert parse_time("14.03.2025", "dmy") == (None, "date_only")
    assert parse_time("3/14/2025", "mdy") == (None, "date_only")


def test_explicit_timezone_is_preserved_as_exact() -> None:
    assert parse_time("2025-03-14T18:58:41+05:00", "iso") == (
        "2025-03-14T18:58:41+05:00",
        "exact",
    )


def test_canonical_record_preserves_source_provenance_with_missing_time() -> None:
    row = {
        "incidentid": "source-17",
        "createddate": "2025-03-14 18:58:41",
        "servicelevel1": "ВОДОСНАБЖЕНИЕ",
        "organizationname": "ГКП",
        "status": "closed",
        "finishdate": "2025-03-15 10:00:00",
        "result": "Работы выполнены",
    }
    record, _ = to_canonical(
        row,
        "KOSTANAY",
        REGIONS["KOSTANAY"],
        "test-salt",
        "2026-09-23T12:00:00+00:00",
        "file://source.csv#sha256=abc123",
    )

    assert record is not None
    assert record["time"]["received_at"] is None
    assert record["time"]["received_at_quality"] == "missing"
    assert record["time"]["source_timezone"] is None
    assert record["ingestion"]["raw_payload_ref"] == "file://source.csv#sha256=abc123"


def test_street_address_variants_are_redacted_before_feature_export() -> None:
    for text in ("ул Каирбекова 75", "Каирбекова 409"):
        cleaned, flags = redact(text)
        assert "Каирбекова" not in cleaned
        assert "75" not in cleaned
        assert "409" not in cleaned
        assert "[АДРЕС]" in cleaned
        assert "address" in flags


def test_person_name_is_redacted_before_feature_export() -> None:
    cleaned, flags = redact("Ответ заявителю: Иванов Иван Иванович")
    assert "Иванов" not in cleaned
    assert "name" in flags


def test_canonical_feature_text_is_redacted_before_return() -> None:
    row = {
        "incidentid": "source-18",
        "createddate": "2025-03-14T18:58:41+05:00",
        "servicelevel1": "ВОДОСНАБЖЕНИЕ",
        "organizationname": "ГКП",
        "status": "closed",
        "finishdate": "2025-03-15T10:00:00+05:00",
        "result": "ул Каирбекова 75 — устранено",
    }
    record, feature_text = to_canonical(
        row,
        "KOSTANAY",
        REGIONS["KOSTANAY"],
        "test-salt",
        "2026-09-23T12:00:00+00:00",
        "file://source.csv#sha256=abc123",
    )

    assert record is not None
    assert record["time"]["received_at_quality"] == "exact"
    assert feature_text == "[АДРЕС] — устранено"


def test_quarantine_record_contains_provenance_without_source_values() -> None:
    raw_row = {"request_subject": "Иванов Иван Иванович, ул Каирбекова 75"}
    entry = quarantine_entry(
        "AKMOLA",
        "SCHEMA_DRIFT_COLUMN_SHIFT",
        raw_row,
        "file://source.csv#sha256=abc123",
    )

    encoded = json.dumps(entry, ensure_ascii=False)
    assert entry["source_ref"] == "file://source.csv#sha256=abc123"
    assert entry["field_names"] == ["request_subject"]
    assert entry["source_row_sha256"]
    assert "row" not in entry
    assert "Иванов" not in encoded
    assert "Каирбекова" not in encoded
    assert "75" not in encoded


def test_research_ingest_does_not_export_executor_prose() -> None:
    record = {
        "ingestion": {"validation_status": "accepted", "warning_codes": []},
        "intake": {"language": "ru"},
        "time": {"received_at_quality": "missing"},
        "governance": {"pii_flags": []},
    }
    canonical, corpus = StringIO(), StringIO()
    report = {
        "totals": {"accepted": 0},
        "language": {},
        "time_quality": {},
        "warnings": {},
        "pii_flags": {},
        "corpus": {"withheld_texts": 0},
    }
    from collections import Counter

    for key in ("totals", "language", "time_quality", "warnings", "pii_flags"):
        report[key] = Counter(report[key])
    regional = {"accepted": 0}
    _emit(record, "Иванов Иван Иванович", canonical, corpus, report, regional, set())
    assert canonical.getvalue()
    assert corpus.getvalue() == ""
    assert report["corpus"]["withheld_texts"] == 1
