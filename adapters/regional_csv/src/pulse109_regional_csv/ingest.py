"""Regional CSV to canonical request adapter for Pulse 109.

Maps the four observed source schema families onto
contracts/canonical_request.schema.json v1.0.0.

Standard library only, streaming, deterministic. Every rejected row lands in
quarantine with a reason code. Nothing is silently dropped.

Source decisions encoded here (see docs/DECISION_LOG.md):
  D1  Karaganda dates are M/D/Y. 87709 rows have a second field above 12,
      so parsing as D/M/Y would corrupt two years of history.
  D2  Turkestan carries lifecycle snapshots: 98876 rows over 52050 incident
      ids. Rows collapse to the latest updateddate per incident id.
  D3  Pavlodar parts 1 and 2 share no identifier and cover the same period.
      They concatenate safely.
  D4  Akmola has 180 lines with unescaped quotes and 145 rows whose
      creation_date is not a date. Those are quarantined, not repaired.
  D5  Coordinates are present in 0.1 to 0.3 percent of rows, so location
      normalization_status is missing for nearly every record.

Usage:
    python pulse109_ingest.py --src DIR --out DIR [--limit N]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import unicodedata
import uuid
from collections import Counter
from datetime import datetime, timezone

csv.field_size_limit(10**9)

SCHEMA_VERSION = "1.0.0"
ADAPTER_VERSION = "1.0.0"
MAPPING_VERSION = "regional-csv/1.0.0"
REDACTION_VERSION = "pii-ru-kz/1.0.0"

KZ_LETTERS = set("әғқңөұүһіӘҒҚҢӨҰҮҺІ")
CYRILLIC = re.compile(r"[а-яёА-ЯЁ]")  # noqa: RUF001
RE_IIN = re.compile(r"\b\d{12}\b")
RE_PHONE = re.compile(r"(?:\+?7|8)[\s\-(]*7\d{2}[\s\-)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}")
RE_HOUSE = re.compile(r"(?i)\b(дом|д\.|кв\.|квартира|үй|пәтер)\s*№?\s*[\d]+[а-яА-Я/\-]*")  # noqa: RUF001
RE_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
# A street number may appear with a street prefix or as a bare street name.
# Keep this deliberately narrow: capitalized Cyrillic place names followed by
# a number, rather than replacing arbitrary numbers in executor prose.
RE_STREET_ADDRESS = re.compile(
    r"(?i)\b(?:ул(?:ица)?\.?\s*)?"
    r"[А-ЯЁӘҒҚҢӨҰҮҺІ][А-ЯЁӘҒҚҢӨҰҮҺІа-яёәғқңөұүһі-]*"  # noqa: RUF001
    r"(?:\s+[А-ЯЁӘҒҚҢӨҰҮҺІ][А-ЯЁӘҒҚҢӨҰҮҺІа-яёәғқңөұүһі-]*){0,2}"  # noqa: RUF001
    r"\s+\d+[А-ЯЁӘҒҚҢӨҰҮҺІа-яёәғқңөұүһі/-]*\b"  # noqa: RUF001
)
RE_PERSON_NAME = re.compile(
    r"\b[А-ЯЁӘҒҚҢӨҰҮҺІ][а-яёәғқңөұүһі'-]+"  # noqa: RUF001
    r"\s+[А-ЯЁӘҒҚҢӨҰҮҺІ][а-яёәғқңөұүһі'-]+"  # noqa: RUF001
    r"(?:\s+[А-ЯЁӘҒҚҢӨҰҮҺІ][а-яёәғқңөұүһі'-]+|\s+[А-ЯЁӘҒҚҢӨҰҮҺІ]\.?)\b"  # noqa: RUF001
)


# --------------------------------------------------------------------------
# region configuration
# --------------------------------------------------------------------------

REGIONS = {
    "PAVLODAR": {
        "files": [
            "Данные по обращениям 109 — Павлодарская область_part_001_of_002.csv",
            "Данные по обращениям 109 — Павлодарская область_part_002_of_002.csv",
        ],
        "family": "appeals",
        "id": "id",
        "created": "create_date",
        "date_fmt": "iso",
        "topic": "category_name",
        "service": "service_name",
        "status": "status",
        "channel_field": None,
        "dedup_key": None,
    },
    "KARAGANDA": {
        "files": ["Обращения граждан 109 - Карагандинская область.csv"],
        "family": "karaganda",
        "id": None,
        "created": "created_date",
        "date_fmt": "mdy",
        "topic": "category",
        "service": "executor_gov_org",
        "status": None,
        "channel_field": "source",
        "address": "appeal_address",
        "district": "district",
        "dedup_key": None,
    },
    "TURKESTAN": {
        "files": ["Обращения жителей 109 - Туркестанская область.csv"],
        "family": "incidents",
        "id": "incidentid",
        "created": "createddate",
        "date_fmt": "iso",
        "topic": "servicelevel1",
        "service": "organizationname",
        "status": "status",
        "channel_field": "source",
        "closed": "finishdate",
        "lat": "xcoordinate",
        "lon": "ycoordinate",
        "dedup_key": ("incidentid", "updateddate"),
    },
    "KOSTANAY": {
        "files": ["Обращения жителей 109 - Костанайская область.csv"],
        "family": "incidents",
        "id": "incidentid",
        "created": "createddate",
        "date_fmt": "iso",
        "topic": "servicelevel1",
        "service": "organizationname",
        "status": "status",
        "channel_field": "source",
        "closed": "finishdate",
        "lat": "xcoordinate",
        "lon": "ycoordinate",
        "result_text": "result",
        "dedup_key": ("incidentid", "updateddate"),
    },
    "VKO": {
        "files": ["Обращения граждан 109 - Восточно-Казахстанская область.csv"],
        "family": "applications",
        "id": "application_number",
        "created": "creation_date",
        "date_fmt": "dmy",
        "topic": "category",
        "service": "service",
        "status": "status",
        "channel_field": "submittal_channel",
        "closed": "closing_date",
        "contractor": "contractor",
        "result_text": "com_exp",
        "pii": ["full_name", "street", "applicant_number"],
        "district": "district",
        "dedup_key": None,
    },
    "ALMATY_OBL": {
        "files": ["Обращения граждан 109 - Алматинская область.csv"],
        "family": "applications",
        "id": "application_number",
        "created": "creation_date",
        "date_fmt": "dmy",
        "topic": "category",
        "service": "service",
        "status": "status",
        "channel_field": "submittal_channel",
        "closed": "closing_date",
        "contractor": "contractor",
        "result_text": "com_exp",
        "dedup_key": None,
    },
    "AKMOLA": {
        "files": ["Обращения граждан 109 - Акмолинская область.csv"],
        "family": "akmola",
        "id": "request_number",
        "created": "creation_date",
        "date_fmt": "iso",
        "topic": "direction",
        "service": "request_subject",
        "status": "status",
        "channel_field": None,
        "district": "region_g_a",
        "dedup_key": None,
    },
}

CHANNEL_MAP = {
    "call-центр": "phone",
    "call центр": "phone",
    "екц 109": "phone",
    "соц. сети (вручную)": "other",
    "соц.сети": "other",
    "мобильное приложение": "mobile",
    "telegram": "telegram",
    "whatsapp": "whatsapp",
    "сайт": "web",
    "портал": "web",
    "email": "email",
}

STATUS_MAP = {
    "closed": "closed",
    "закрыто": "closed",
    "закрыт": "closed",
    "закрыто инициатором": "cancelled",
    "выполнено": "resolved",
    "передано в службу": "assigned",
    "в работе": "in_progress",
    "новое": "new",
    "открыто": "triage",
    "отменено": "cancelled",
}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


UUID_NS = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


def request_uuid(region_id: str, source_id: str, salt: str) -> str:
    """Deterministic UUIDv5 so a re-ingest of the same row yields the same id."""
    return str(uuid.uuid5(UUID_NS, f"{salt}|{region_id}|{source_id}"))


def token(value: str, salt: str) -> str:
    """Stable opaque token.

    The salt must come from the secret store in production.
    The default only serves local reproducibility.
    """
    return "tok_" + hashlib.sha256((salt + "|" + value).encode("utf-8")).hexdigest()[:32]


def detect_language(*parts: str) -> str:
    text = " ".join(p for p in parts if p)
    if not text.strip():
        return "unknown"
    has_kz = bool(set(text) & KZ_LETTERS)
    has_cyr = bool(CYRILLIC.search(text))
    if has_kz and has_cyr:
        return "mixed"
    if has_kz:
        return "kk"
    if has_cyr:
        return "ru"
    return "unknown"


def parse_time(raw: str, fmt: str):
    """Return (iso_or_None, quality). Quality follows the canonical enum."""
    raw = (raw or "").strip()
    if not raw or raw in ("-infinity", "infinity", "NULL", "null"):
        return None, "missing"

    # Date-only values carry a calendar date, not an instant. Preserve that
    # distinction instead of manufacturing midnight UTC.
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", raw)
    if m:
        y, mo, d = (int(x) for x in m.groups())
        try:
            datetime(y, mo, d)  # validate without assigning a timezone
            return None, "date_only"
        except ValueError:
            return None, "missing"

    # Preserve explicit offsets when the source provides one. A naive source
    # timestamp has unknown business timezone, so it stays missing.
    if fmt == "iso":
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                return parsed.isoformat(), "exact"
            return None, "missing"
        except ValueError:
            pass

    if fmt == "dmy":
        m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})(?:\s+(\d{2}):(\d{2}):(\d{2}))?", raw)
        if m:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                if m.group(4):
                    # These regional formats have no timezone field.
                    return None, "missing"
                datetime(y, mo, d)  # validate the date
                return None, "date_only"
            except ValueError:
                return None, "missing"

    if fmt == "mdy":
        m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})(?:\s+(\d{1,2}):(\d{2}))?", raw)
        if m:
            mo, d = int(m.group(1)), int(m.group(2))
            y = int(m.group(3))
            y = y + 2000 if y < 100 else y
            try:
                if m.group(4):
                    # These regional formats have no timezone field.
                    return None, "missing"
                datetime(y, mo, d)  # validate the date
                return None, "date_only"
            except ValueError:
                return None, "missing"

    return None, "missing"


def redact(text: str):
    """Deterministic PII redaction. Returns (clean_text, flags)."""
    if not text:
        return text, []
    flags = []
    out = text
    if RE_IIN.search(out):
        out = RE_IIN.sub("[ИИН]", out)
        flags.append("iin")
    if RE_PHONE.search(out):
        out = RE_PHONE.sub("[ТЕЛЕФОН]", out)
        flags.append("phone")
    if RE_EMAIL.search(out):
        out = RE_EMAIL.sub("[EMAIL]", out)
        flags.append("email")
    if RE_HOUSE.search(out):
        out = RE_HOUSE.sub("[АДРЕС]", out)
        flags.append("address")
    if RE_STREET_ADDRESS.search(out):
        out = RE_STREET_ADDRESS.sub("[АДРЕС]", out)
        flags.append("address")
    if RE_PERSON_NAME.search(out):
        out = RE_PERSON_NAME.sub("[ПЕРСОНАЛЬНЫЕ ДАННЫЕ]", out)
        flags.append("name")
    return out, flags


def norm_key(value: str) -> str:
    return unicodedata.normalize("NFKC", (value or "").strip().lower())


def clean(value: str) -> str:
    v = (value or "").replace("\xa0", " ").strip()
    return "" if v.lower() in ("null", "none", "nan", "-") else v


# --------------------------------------------------------------------------
# mapping
# --------------------------------------------------------------------------


def to_canonical(row, region_id, cfg, salt, observed_at, raw_ref):
    warnings = []
    pii_flags = []

    created_raw = clean(row.get(cfg["created"], ""))
    received_at, quality = parse_time(created_raw, cfg["date_fmt"])
    if quality == "missing" and created_raw:
        warnings.append("TIME_UNPARSEABLE")

    # D4: a non-date in the date column means the row shifted
    if cfg["family"] == "akmola" and created_raw and quality == "missing":
        return None, "SCHEMA_DRIFT_COLUMN_SHIFT"

    src_id = clean(row.get(cfg["id"], "")) if cfg["id"] else ""
    if not src_id:
        src_id = sha(json.dumps(row, ensure_ascii=False, sort_keys=True))[:16]
        warnings.append("SYNTHETIC_SOURCE_ID")

    topic = clean(row.get(cfg["topic"], ""))
    service = clean(row.get(cfg["service"], ""))
    if not topic:
        warnings.append("TOPIC_MISSING")
    if not service:
        warnings.append("SERVICE_MISSING")

    channel = "import"
    if cfg.get("channel_field"):
        channel = CHANNEL_MAP.get(norm_key(row.get(cfg["channel_field"], "")), "other")

    status_raw = norm_key(row.get(cfg["status"], "")) if cfg.get("status") else ""
    current_status = STATUS_MAP.get(status_raw)
    if status_raw and not current_status:
        warnings.append("STATUS_UNMAPPED")

    closed_at = None
    if cfg.get("closed"):
        closed_at, _ = parse_time(clean(row.get(cfg["closed"], "")), cfg["date_fmt"])

    # free text written by the executor after closure, never citizen text
    result_text = clean(row.get(cfg["result_text"], "")) if cfg.get("result_text") else ""
    result_text, rflags = redact(result_text)
    pii_flags += rflags

    language = detect_language(result_text, topic, service)

    # D5: coordinates exist in well under one percent of rows
    lat = lon = None
    norm_status = "missing"
    if cfg.get("lat"):
        try:
            lat = float(clean(row.get(cfg["lat"], "")))
            lon = float(clean(row.get(cfg["lon"], "")))
            norm_status = "exact"
        except (TypeError, ValueError):
            lat = lon = None
    address_ref = None
    if cfg.get("address"):
        addr = clean(row.get(cfg["address"], ""))
        if addr:
            address_ref = token(addr, salt)
            norm_status = "approximate"
            pii_flags.append("address")

    for field in cfg.get("pii", []):
        if clean(row.get(field, "")):
            pii_flags.append(field)

    geo_id = None
    if cfg.get("district"):
        geo_id = clean(row.get(cfg["district"], "")) or None

    contractor = None
    if cfg.get("contractor"):
        contractor = clean(row.get(cfg["contractor"], "")) or None

    rec = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_uuid(region_id, src_id, salt),
        "source": {
            "system": f"csv-export:{region_id.lower()}",
            "request_id": src_id,
            "region_id": region_id,
            "export_id": None,
            "source_record_checksum": sha("|".join(f"{k}={v}" for k, v in sorted(row.items()))),
        },
        "intake": {
            "channel": channel,
            "language": language,
            "raw_text_ref": None,  # B02: no citizen text exists in any export
            "transcript_ref": None,
            "media_refs": [],
            "citizen_token": None,
            "selected_attributes": {"topic_label": topic, "service_label": service},
        },
        "time": {
            "received_at": received_at,
            "received_at_quality": quality,
            "source_timezone": None,
            "observed_at": observed_at,
            "closed_at": closed_at,
        },
        "location": {
            "address_private_ref": address_ref,
            "geo_id": geo_id,
            "object_id": None,
            "latitude": lat,
            "longitude": lon,
            "precision_m": None,
            "normalization_status": norm_status,
        },
        "execution": {
            "sla_policy_version": None,
            "due_at": None,
            "contractor_id": contractor,
            "result_ref": sha(result_text)[:32] if result_text else None,
            "evidence_refs": [],
        },
        "incident": {
            "incident_id": None,
            "membership_state": "none",
            "duplicate_score": None,
            "proposal_reason_codes": [],
        },
        "governance": {
            "legal_basis": "hackathon_export_pending_confirmation",  # B10 open
            "retention_class": "evaluation_only",
            "pii_flags": sorted(set(pii_flags)),
            "access_scope": [f"region:{region_id}"],
            "redaction_version": REDACTION_VERSION,
            "deletion_due_at": None,
        },
        "ingestion": {
            "adapter_id": f"regional-csv-{cfg['family']}",
            "adapter_version": ADAPTER_VERSION,
            "schema_mapping_version": MAPPING_VERSION,
            "ingested_at": observed_at,
            "raw_payload_ref": raw_ref,
            "validation_status": "accepted_with_warnings" if warnings else "accepted",
            "warning_codes": sorted(set(warnings)),
        },
    }
    if current_status:
        rec["execution"]["current_status"] = current_status

    return rec, (result_text or None)


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------


def _emit(rec, text, fh_canon, fh_corpus, report, rstat, seen_texts):
    fh_canon.write(json.dumps(rec, ensure_ascii=False) + "\n")
    rstat["accepted"] += 1
    status = rec["ingestion"]["validation_status"]
    report["totals"][status] += 1
    report["language"][rec["intake"]["language"]] += 1
    report["time_quality"][rec["time"]["received_at_quality"]] += 1
    for w in rec["ingestion"]["warning_codes"]:
        report["warnings"][w] += 1
    for p in rec["governance"]["pii_flags"]:
        report["pii_flags"][p] += 1

    # B10 remains open. Regex masking is diagnostic only and cannot authorize
    # exporting executor prose to a feature corpus. Keep the output file empty
    # until a private approved redaction pipeline replaces this research path.
    if text and len(text) >= 8:
        report["corpus"]["withheld_texts"] += 1


def quarantine_entry(region_id: str, reason: str, row: dict, source_ref: str) -> dict:
    """Return a content-free quarantine record with stable source provenance."""
    serialized = json.dumps(row, ensure_ascii=False, sort_keys=True)
    return {
        "region": region_id,
        "reason": reason,
        "source_ref": source_ref,
        "source_row_sha256": sha(serialized),
        "field_names": sorted(str(key) for key in row if key),
    }


def run(src_dir, out_dir, salt, limit=None):
    os.makedirs(out_dir, exist_ok=True)
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    fh_canon = open(os.path.join(out_dir, "canonical.jsonl"), "w", encoding="utf-8")
    fh_quar = open(os.path.join(out_dir, "quarantine.jsonl"), "w", encoding="utf-8")
    fh_corpus = open(os.path.join(out_dir, "retrieval_corpus.jsonl"), "w", encoding="utf-8")

    report = {
        "generated_at": observed_at,
        "adapter_version": ADAPTER_VERSION,
        "mapping_version": MAPPING_VERSION,
        "redaction_version": REDACTION_VERSION,
        "totals": {
            "input_rows": 0,
            "accepted": 0,
            "accepted_with_warnings": 0,
            "quarantined": 0,
            "deduplicated": 0,
        },
        "regions": {},
        "language": Counter(),
        "time_quality": Counter(),
        "warnings": Counter(),
        "quarantine_reasons": Counter(),
        "pii_flags": Counter(),
        "corpus": {"texts": 0, "unique_texts": 0, "withheld_texts": 0, "by_language": Counter()},
    }
    seen_texts = set()

    for region_id, cfg in REGIONS.items():
        rstat = {"input_rows": 0, "accepted": 0, "quarantined": 0, "deduplicated": 0, "files": []}
        dedup_pool = {}

        for fname in cfg["files"]:
            path = os.path.join(src_dir, fname)
            if not os.path.exists(path):
                print(f"  MISSING {fname}", file=sys.stderr)
                continue
            raw_ref = f"file://{fname}#sha256={sha(fname)[:16]}"
            rstat["files"].append(fname)

            with open(path, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                ncols = len(reader.fieldnames or [])
                for row in reader:
                    rstat["input_rows"] += 1
                    report["totals"]["input_rows"] += 1
                    if limit and rstat["input_rows"] > limit:
                        break

                    if None in row or len([k for k in row if k]) != ncols:
                        report["quarantine_reasons"]["FIELD_COUNT_MISMATCH"] += 1
                        report["totals"]["quarantined"] += 1
                        rstat["quarantined"] += 1
                        fh_quar.write(
                            json.dumps(
                                quarantine_entry(
                                    region_id,
                                    "FIELD_COUNT_MISMATCH",
                                    {k: v for k, v in row.items() if k},
                                    raw_ref,
                                ),
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                        continue

                    rec, extra = to_canonical(row, region_id, cfg, salt, observed_at, raw_ref)
                    if rec is None:
                        report["quarantine_reasons"][extra] += 1
                        report["totals"]["quarantined"] += 1
                        rstat["quarantined"] += 1
                        fh_quar.write(
                            json.dumps(
                                quarantine_entry(region_id, extra, row, raw_ref),
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                        continue

                    # D2: collapse lifecycle snapshots to the latest update
                    if cfg["dedup_key"]:
                        kf, tf = cfg["dedup_key"]
                        key = clean(row.get(kf, ""))
                        stamp = clean(row.get(tf, ""))
                        prev = dedup_pool.get(key)
                        if prev is None or stamp > prev[0]:
                            dedup_pool[key] = (stamp, rec, extra)
                        continue

                    _emit(rec, extra, fh_canon, fh_corpus, report, rstat, seen_texts)

        for _key, (_stamp, rec, extra) in dedup_pool.items():
            _emit(rec, extra, fh_canon, fh_corpus, report, rstat, seen_texts)
        if cfg["dedup_key"]:
            collapsed = rstat["input_rows"] - rstat["quarantined"] - len(dedup_pool)
            rstat["deduplicated"] = collapsed
            report["totals"]["deduplicated"] += collapsed

        report["regions"][region_id] = rstat
        print(
            f"  {region_id:<11} in {rstat['input_rows']:>8,}  out {rstat['accepted']:>8,}  "
            f"dedup {rstat['deduplicated']:>6,}  quar {rstat['quarantined']:>5,}",
            file=sys.stderr,
        )

    for fh in (fh_canon, fh_quar, fh_corpus):
        fh.close()

    report["corpus"]["unique_texts"] = len(seen_texts)
    for key in ("language", "time_quality", "warnings", "quarantine_reasons", "pii_flags"):
        report[key] = dict(sorted(report[key].items(), key=lambda kv: -kv[1]))
    report["corpus"]["by_language"] = dict(report["corpus"]["by_language"])

    with open(os.path.join(out_dir, "dq_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--salt", default=os.environ.get("PULSE109_TOKEN_SALT", "local-dev-salt"))
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    print("ingest starting", file=sys.stderr)
    rep = run(a.src, a.out, a.salt, a.limit)
    t = rep["totals"]
    print(
        f"\ninput {t['input_rows']:,} -> accepted {t['accepted'] + t['accepted_with_warnings']:,} "
        f"(dedup {t['deduplicated']:,}, quarantined {t['quarantined']:,})",
        file=sys.stderr,
    )
    print(f"retrieval corpus: {rep['corpus']['unique_texts']:,} unique texts", file=sys.stderr)


if __name__ == "__main__":
    main()
