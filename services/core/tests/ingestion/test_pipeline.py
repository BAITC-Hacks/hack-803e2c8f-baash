import json
from pathlib import Path
from typing import Any

from pulse109.ingestion.pipeline import ingest_jsonl, load_schema

ROOT = Path(__file__).resolve().parents[4]
SCHEMA = load_schema(ROOT / "contracts/canonical_request.schema.json")


def row(request_id: str = "REQ-1", **extra: Any) -> str:
    value: dict[str, Any] = {
        "access_scope": ["region:ALA", "purpose:test"],
        "channel": "web",
        "language": "ru",
        "legal_basis": "SYNTHETIC_TEST_ONLY",
        "pii_flags": ["none"],
        "received_at": "2026-09-10T10:00:00+05:00",
        "region_id": "ALA",
        "retention_class": "synthetic-ephemeral",
        "source_request_id": request_id,
        "source_system": "synthetic-crm",
        "source_timezone": "Asia/Almaty",
    }
    value.update(extra)
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def ingest(*lines: str) -> Any:
    return ingest_jsonl(
        lines,
        source_system="synthetic-crm",
        run_id="run-1",
        observed_at="2026-09-11T00:00:00+00:00",
        schema=SCHEMA,
        expected_regions=("ALA", "AST"),
    )


def test_valid_record_has_contract_shape_and_provenance() -> None:
    result = ingest(row())

    assert len(result.accepted) == 1
    assert not result.quarantine
    canonical = result.accepted[0]
    assert canonical["ingestion"]["raw_payload_ref"].startswith("raw://sha256/")
    assert canonical["source"]["source_record_checksum"]
    assert canonical["time"]["received_at_quality"] == "exact"
    assert canonical["governance"]["legal_basis"] == "SYNTHETIC_TEST_ONLY"


def test_missing_and_date_only_time_do_not_invent_instants() -> None:
    result = ingest(
        row("REQ-2", received_at=None, source_timezone=None),
        row("REQ-3", received_at="2026-09-10", source_timezone="Asia/Almaty"),
    )

    assert [item["time"]["received_at_quality"] for item in result.accepted] == [
        "missing",
        "date_only",
    ]
    assert [item["time"]["received_at"] for item in result.accepted] == [None, None]
    assert result.warning_count == 2


def test_naive_time_requires_approved_source_timezone() -> None:
    accepted = ingest(row("REQ-4", received_at="2026-09-10T10:00:00"))
    rejected = ingest(row("REQ-5", received_at="2026-09-10T10:00:00", source_timezone=None))

    assert accepted.accepted[0]["time"]["received_at_quality"] == "source_tz_assumed"
    assert rejected.quarantine[0].error_code == "TIME_INVALID"


def test_exact_duplicate_is_noop_and_conflict_is_quarantined() -> None:
    first = row("REQ-6")
    result = ingest(first, first, row("REQ-6", language="kk"))

    assert len(result.accepted) == 1
    assert result.duplicate_count == 1
    assert result.quarantine[0].error_code == "DUPLICATE_CONFLICT"


def test_unknown_column_and_invalid_time_are_quarantined() -> None:
    result = ingest(row("REQ-7", unexpected="x"), row("REQ-8", received_at="bad"))

    assert [item.error_code for item in result.quarantine] == ["SCHEMA_DRIFT", "TIME_INVALID"]
    assert result.drift_count == 1
    assert all(item.raw_payload_ref.startswith("raw://sha256/") for item in result.quarantine)


def test_report_marks_missing_regions_and_is_deterministic() -> None:
    first = ingest(row("REQ-9"))
    second = ingest(row("REQ-9"))

    assert first.report() == second.report()
    assert first.report()["missing_regions"] == ["AST"]
    assert first.report()["synthetic_only"] is True
