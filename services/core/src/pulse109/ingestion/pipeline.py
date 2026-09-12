"""Deterministic raw JSONL to canonical request conversion."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_VERSION = "1.0.0"
PARSER_VERSION = "pulse109-jsonl/1.0.0"
MAPPING_VERSION = "synthetic-source/1.0.0"
KNOWN_CHANNELS = {
    "phone",
    "web",
    "mobile",
    "telegram",
    "whatsapp",
    "email",
    "walk_in",
    "import",
    "other",
}
KNOWN_LANGUAGES = {"kk", "ru", "mixed", "unknown"}
KNOWN_STATUSES = {
    "new",
    "triage",
    "assigned",
    "in_progress",
    "resolved",
    "closed",
    "reopened",
    "cancelled",
}
EXPECTED_FIELDS = {
    "access_scope",
    "channel",
    "citizen_token",
    "closed_at",
    "export_id",
    "geo_id",
    "language",
    "latitude",
    "legal_basis",
    "longitude",
    "media_refs",
    "object_id",
    "pii_flags",
    "precision_m",
    "raw_text_ref",
    "received_at",
    "region_id",
    "retention_class",
    "selected_attributes",
    "source_request_id",
    "source_system",
    "source_timezone",
    "status",
    "transcript_ref",
}
REQUIRED_FIELDS = {
    "access_scope",
    "channel",
    "legal_basis",
    "region_id",
    "retention_class",
    "source_request_id",
    "source_system",
}


@dataclass(frozen=True)
class ParsedTime:
    value: str | None
    quality: str
    source_timezone: str | None


@dataclass
class QuarantineItem:
    line_number: int
    raw_hash: str
    source_row_ref: str
    raw_payload_ref: str
    error_code: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "line_number": self.line_number,
            "message": self.message,
            "raw_hash": self.raw_hash,
            "raw_payload_ref": self.raw_payload_ref,
            "source_row_ref": self.source_row_ref,
        }


@dataclass
class ImportResult:
    source_system: str
    run_id: str
    observed_at: str
    expected_regions: tuple[str, ...] = ()
    accepted: list[dict[str, Any]] = field(default_factory=list)
    quarantine: list[QuarantineItem] = field(default_factory=list)
    duplicate_count: int = 0
    warning_count: int = 0
    drift_count: int = 0
    input_count: int = 0
    missing_time_count: int = 0
    date_only_count: int = 0
    assumed_timezone_count: int = 0
    batch_checksum: str = ""

    def report(self) -> dict[str, Any]:
        errors: dict[str, int] = {}
        for item in self.quarantine:
            errors[item.error_code] = errors.get(item.error_code, 0) + 1
        regions = sorted({row["source"]["region_id"] for row in self.accepted})
        return {
            "accepted": len(self.accepted),
            "accepted_with_warnings": self.warning_count,
            "canonical_contract_version": SCHEMA_VERSION,
            "date_only_business_time": self.date_only_count,
            "duplicates": self.duplicate_count,
            "error_counts": dict(sorted(errors.items())),
            "expected_regions": list(self.expected_regions),
            "input_rows": self.input_count,
            "mapping_version": MAPPING_VERSION,
            "missing_business_time": self.missing_time_count,
            "missing_regions": sorted(set(self.expected_regions) - set(regions)),
            "observed_at": self.observed_at,
            "parser_version": PARSER_VERSION,
            "quarantined": len(self.quarantine),
            "raw_payload_sha256": self.batch_checksum,
            "regions_present": regions,
            "report_version": "1.0.0",
            "run_id": self.run_id,
            "schema_drift": self.drift_count,
            "source_system": self.source_system,
            "source_timezone_assumed": self.assumed_timezone_count,
            "synthetic_only": True,
        }


def _parse_observed_at(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("observed_at must be RFC 3339") from exc
    if parsed.tzinfo is None:
        raise ValueError("observed_at requires an explicit UTC offset")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("source_timezone must be a valid IANA timezone") from exc


def _parse_business_time(value: Any, source_timezone: Any, field_name: str) -> ParsedTime:
    if value is None or value == "":
        return ParsedTime(None, "missing", None)
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or null")
    if len(value) == 10:
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"invalid date for {field_name}") from exc
        timezone_name = str(source_timezone) if source_timezone else None
        if timezone_name:
            _load_timezone(timezone_name)
        return ParsedTime(None, "date_only", timezone_name)

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid datetime for {field_name}") from exc

    if parsed.tzinfo is None:
        if not source_timezone:
            raise ValueError(f"timezone required for {field_name}")
        timezone_name = str(source_timezone)
        zone = _load_timezone(timezone_name)
        first = parsed.replace(tzinfo=zone, fold=0)
        second = parsed.replace(tzinfo=zone, fold=1)
        if first.utcoffset() != second.utcoffset():
            raise ValueError(f"ambiguous local datetime for {field_name}")
        return ParsedTime(first.isoformat(), "source_tz_assumed", timezone_name)

    timezone_name = str(source_timezone) if source_timezone else str(parsed.tzinfo)
    if source_timezone:
        _load_timezone(str(source_timezone))
    return ParsedTime(parsed.isoformat(), "exact", timezone_name)


def _validate_source_row(row: dict[str, Any], source_system: str) -> None:
    unknown = sorted(set(row) - EXPECTED_FIELDS)
    if unknown:
        raise ValueError(f"unknown columns: {','.join(unknown)}")
    missing = sorted(field for field in REQUIRED_FIELDS if row.get(field) in (None, "", []))
    if missing:
        raise ValueError(f"missing required fields: {','.join(missing)}")
    if row["source_system"] != source_system:
        raise ValueError("source system mismatch")
    if row["channel"] not in KNOWN_CHANNELS:
        raise ValueError("unknown channel")
    if row.get("language", "unknown") not in KNOWN_LANGUAGES:
        raise ValueError("unknown language")
    if row.get("status") and row["status"] not in KNOWN_STATUSES:
        raise ValueError("unknown status")
    if not isinstance(row["access_scope"], list) or not all(
        isinstance(item, str) and item for item in row["access_scope"]
    ):
        raise ValueError("access_scope must contain opaque scope strings")


def _canonical(
    row: dict[str, Any], raw_hash: str, source_system: str, observed_at: str, adapter_version: str
) -> tuple[dict[str, Any], str]:
    received = _parse_business_time(
        row.get("received_at"), row.get("source_timezone"), "received_at"
    )
    closed = _parse_business_time(row.get("closed_at"), row.get("source_timezone"), "closed_at")
    if received.value and closed.value:
        if datetime.fromisoformat(closed.value) < datetime.fromisoformat(received.value):
            raise ValueError("closed_at cannot precede received_at")

    warning_codes = []
    if received.quality != "exact":
        warning_codes.append(f"RECEIVED_AT_{received.quality.upper()}")
    if row.get("closed_at") and closed.quality != "exact":
        warning_codes.append(f"CLOSED_AT_{closed.quality.upper()}")
    validation_status = "accepted_with_warnings" if warning_codes else "accepted"
    request_id = uuid.uuid5(
        uuid.NAMESPACE_URL, f"pulse109:{source_system}:{row['source_request_id']}"
    )
    raw_payload_ref = f"raw://sha256/{raw_hash}"

    location_present = bool(row.get("geo_id") or row.get("object_id"))
    canonical: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "request_id": str(request_id),
        "source": {
            "system": source_system,
            "request_id": str(row["source_request_id"]),
            "region_id": row["region_id"],
            "export_id": row.get("export_id"),
            "source_record_checksum": raw_hash,
        },
        "intake": {
            "channel": row["channel"],
            "language": row.get("language", "unknown"),
            "raw_text_ref": row.get("raw_text_ref"),
            "transcript_ref": row.get("transcript_ref"),
            "media_refs": row.get("media_refs", []),
            "citizen_token": row.get("citizen_token"),
            "selected_attributes": row.get("selected_attributes", {}),
        },
        "time": {
            "received_at": received.value,
            "received_at_quality": received.quality,
            "source_timezone": received.source_timezone,
            "observed_at": observed_at,
            "closed_at": closed.value,
        },
        "location": {
            "address_private_ref": None,
            "geo_id": row.get("geo_id"),
            "object_id": row.get("object_id"),
            "latitude": row.get("latitude"),
            "longitude": row.get("longitude"),
            "precision_m": row.get("precision_m"),
            "normalization_status": "approximate" if location_present else "missing",
        },
        "governance": {
            "legal_basis": row["legal_basis"],
            "retention_class": row["retention_class"],
            "pii_flags": row.get("pii_flags", ["none"]),
            "access_scope": row["access_scope"],
            "redaction_version": None,
            "deletion_due_at": None,
        },
        "ingestion": {
            "adapter_id": source_system,
            "adapter_version": adapter_version,
            "schema_mapping_version": MAPPING_VERSION,
            "ingested_at": observed_at,
            "raw_payload_ref": raw_payload_ref,
            "validation_status": validation_status,
            "warning_codes": warning_codes,
        },
    }
    if row.get("status"):
        canonical["execution"] = {"current_status": row["status"]}
    return canonical, received.quality


def _error_code(message: str) -> str:
    if "conflicting duplicate" in message:
        return "DUPLICATE_CONFLICT"
    if any(token in message for token in ("unknown columns", "unknown status", "unknown channel")):
        return "SCHEMA_DRIFT"
    if any(token in message for token in ("date", "timezone", "observed_at", "closed_at")):
        return "TIME_INVALID"
    return "SCHEMA_VALIDATION_FAILED"


def ingest_jsonl(
    lines: Iterable[str],
    *,
    source_system: str,
    run_id: str,
    observed_at: str,
    adapter_version: str = "1.0.0",
    schema: dict[str, Any] | None = None,
    expected_regions: Iterable[str] = (),
) -> ImportResult:
    normalized_observed_at = _parse_observed_at(observed_at)
    result = ImportResult(
        source_system,
        run_id,
        normalized_observed_at,
        tuple(sorted(set(expected_regions))),
    )
    identities: dict[tuple[str, str], str] = {}
    validator = (
        Draft202012Validator(schema, format_checker=FormatChecker()) if schema is not None else None
    )
    batch_hasher = hashlib.sha256()

    for line_number, original_line in enumerate(lines, 1):
        line = original_line.rstrip("\r\n")
        if not line:
            continue
        result.input_count += 1
        batch_hasher.update(line.encode("utf-8"))
        batch_hasher.update(b"\n")
        raw_hash = hashlib.sha256(line.encode("utf-8")).hexdigest()
        raw_payload_ref = f"raw://sha256/{raw_hash}"
        source_row_ref = f"{source_system}:{line_number}"
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("row must be an object")
            _validate_source_row(row, source_system)
            identity = (source_system, str(row["source_request_id"]))
            if identity in identities:
                if identities[identity] == raw_hash:
                    result.duplicate_count += 1
                    continue
                raise ValueError("conflicting duplicate payload")
            canonical, time_quality = _canonical(
                row, raw_hash, source_system, normalized_observed_at, adapter_version
            )
            if validator is not None:
                errors = sorted(
                    validator.iter_errors(canonical), key=lambda error: list(error.path)
                )
                if errors:
                    detail = "; ".join(error.message for error in errors[:3])
                    raise ValueError(f"canonical schema validation failed: {detail}")
            identities[identity] = raw_hash
            result.accepted.append(canonical)
            if time_quality != "exact":
                result.warning_count += 1
            if time_quality == "missing":
                result.missing_time_count += 1
            elif time_quality == "date_only":
                result.date_only_count += 1
            elif time_quality == "source_tz_assumed":
                result.assumed_timezone_count += 1
        except (ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
            message = str(exc)
            code = _error_code(message)
            if code == "SCHEMA_DRIFT":
                result.drift_count += 1
            result.quarantine.append(
                QuarantineItem(
                    line_number,
                    raw_hash,
                    source_row_ref,
                    raw_payload_ref,
                    code,
                    message,
                )
            )

    result.batch_checksum = batch_hasher.hexdigest()
    return result


def load_schema(path: str | Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    return value
