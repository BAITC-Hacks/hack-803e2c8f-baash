"""Generate a reproducible EDA report for an approved canonical dataset.

A notebook somebody ran once is not evidence. This writes the same report from
the same file every time, records the hash of what it read, and states its own
limits, so a reviewer can rerun it and compare.

Usage:
    uv run python -m analytics.offline.report \
        --input /secure/data/canonical.jsonl \
        --output /secure/reports/eda
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .manifest import build_manifest
from .quality import assess, weakest_dimensions
from .temporal import profile

LIMITS = (
    "This is observational exploration of historical exports. Nothing here "
    "establishes cause. A difference between two regions is a difference in "
    "what was recorded, which may be a difference in the city, in the process "
    "or in the export.",
    "Regions cover different periods. Raw volume must never be compared "
    "between them without reading the coverage column beside it.",
    "Counts that depend on the hour or the weekday use only records whose "
    "business time is trustworthy. The trusted share is stated per region.",
    "No citizen text exists in these exports (B02), so nothing here describes "
    "what people actually wrote.",
)


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def build_report(input_path: Path, *, synthetic: bool) -> dict[str, Any]:
    manifest, records = build_manifest(input_path, synthetic=synthetic)
    regions = assess(records)
    temporal = profile(records)

    channels: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    topics: Counter[str] = Counter()
    services: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    time_quality: Counter[str] = Counter()
    by_region_language: dict[str, Counter[str]] = defaultdict(Counter)

    for record in records:
        intake = record.get("intake") or {}
        attributes = intake.get("selected_attributes") or {}
        execution = record.get("execution") or {}
        time_section = record.get("time") or {}
        region = str((record.get("source") or {}).get("region_id") or "UNKNOWN")

        if channel := intake.get("channel"):
            channels[str(channel)] += 1
        if language := intake.get("language"):
            languages[str(language)] += 1
            by_region_language[region][str(language)] += 1
        if topic := attributes.get("topic_label"):
            topics[str(topic)] += 1
        if service := attributes.get("service_label"):
            services[str(service)] += 1
        if status := execution.get("current_status"):
            statuses[str(status)] += 1
        time_quality[str(time_section.get("received_at_quality") or "unset")] += 1

    return {
        "manifest": manifest.to_dict(),
        "quality": {
            "regions": [region.to_dict() for region in regions],
            "weakest": [
                {"region_id": region, "dimension": name, "ratio": ratio}
                for region, name, ratio in weakest_dimensions(regions)
            ],
        },
        "temporal": [item.to_dict() for item in temporal],
        "distributions": {
            "channels": dict(channels.most_common(20)),
            "languages": dict(languages.most_common(20)),
            "topics": dict(topics.most_common(25)),
            "services": dict(services.most_common(25)),
            "statuses": dict(statuses.most_common(25)),
            "received_at_quality": dict(time_quality.most_common()),
            "language_by_region": {
                region: dict(counter.most_common(10))
                for region, counter in sorted(by_region_language.items())
            },
        },
        "limits": list(LIMITS),
    }


def render_markdown(report: dict[str, Any]) -> str:
    manifest = report["manifest"]
    lines: list[str] = []
    add = lines.append

    add("# Canonical dataset exploration")
    add("")
    add(f"Dataset `{manifest['dataset_id']}`, {manifest['row_count']:,} records.")
    add(f"Content hash `{manifest['dataset_hash'][:16]}…`, generated {manifest['generated_at']}.")
    if manifest["synthetic"]:
        add("")
        add("**This dataset is synthetic.** No figure here describes a real city.")
    add("")

    add("## Provenance")
    add("")
    add("| Field | Value |")
    add("| --- | --- |")
    add(f"| Rows | {manifest['row_count']:,} |")
    add(f"| Schema versions | {', '.join(manifest['schema_versions']) or '—'} |")
    add(f"| Mapping versions | {', '.join(manifest['mapping_versions']) or '—'} |")
    add(f"| Adapters | {', '.join(manifest['adapters']) or '—'} |")
    add(f"| Regions | {', '.join(manifest['regions']) or '—'} |")
    add(f"| Earliest received | {manifest['coverage']['earliest_received_at'] or '—'} |")
    add(f"| Latest received | {manifest['coverage']['latest_received_at'] or '—'} |")
    add("")
    for note in manifest["notes"]:
        add(f"> {note}")
        add("")

    add("## Data quality by region")
    add("")
    add("Six dimensions rather than one score, because a single number does not")
    add("tell anyone what to fix.")
    add("")
    header = (
        ["Region", "Rows", "Coverage"]
        + [dimension["name"] for dimension in report["quality"]["regions"][0]["dimensions"]]
        if report["quality"]["regions"]
        else ["Region", "Rows", "Coverage"]
    )
    add("| " + " | ".join(header) + " |")
    add("| " + " | ".join(["---"] * len(header)) + " |")
    for region in report["quality"]["regions"]:
        coverage = region["coverage"]
        span = (
            f"{(coverage['earliest_received_at'] or '—')[:10]} … "
            f"{(coverage['latest_received_at'] or '—')[:10]}"
        )
        row = [region["region_id"], f"{region['row_count']:,}", span]
        row += [_pct(dimension["ratio"]) for dimension in region["dimensions"]]
        add("| " + " | ".join(row) + " |")
    add("")

    if report["quality"]["weakest"]:
        add("### Look here first")
        add("")
        add("Dimensions below 95 percent, weakest first.")
        add("")
        for item in report["quality"]["weakest"]:
            add(f"- `{item['region_id']}` · {item['dimension']} · {_pct(item['ratio'])}")
        add("")
    else:
        add("### Look here first")
        add("")
        add("Every dimension in every region is at or above 95 percent.")
        add("")

    add("## Arrival patterns")
    add("")
    add("Hour and weekday counts use only records whose business time can be")
    add("trusted. The trusted share is stated so a reader knows how much of the")
    add("region these charts actually describe.")
    add("")
    add("| Region | Trusted rows | Trusted share | Observed days | Mean per day | Busiest hours |")
    add("| --- | --- | --- | --- | --- | --- |")
    for item in report["temporal"]:
        busiest = ", ".join(f"{entry['hour']:02d}" for entry in item["busiest_hours"]) or "—"
        add(
            f"| {item['region_id']} | {item['trusted_rows']:,} | "
            f"{_pct(item['trusted_share'])} | {item['observed_days']:,} | "
            f"{item['mean_per_observed_day'] or '—'} | {busiest} |"
        )
    add("")

    distributions = report["distributions"]
    add("## Distributions")
    add("")
    for title, key in (
        ("Received time quality", "received_at_quality"),
        ("Channels", "channels"),
        ("Languages", "languages"),
        ("Statuses", "statuses"),
        ("Topics", "topics"),
    ):
        values = distributions.get(key) or {}
        if not values:
            continue
        add(f"### {title}")
        add("")
        total = sum(values.values()) or 1
        for name, count in list(values.items())[:12]:
            add(f"- `{name}` · {count:,} · {count / total * 100:.1f}%")
        add("")

    add("## Limits")
    add("")
    for limit in report["limits"]:
        add(f"- {limit}")
    add("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="mark the dataset as synthetic, which the report then states on every page",
    )
    args = parser.parse_args()

    report = build_report(args.input, synthetic=args.synthetic)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "CURRENT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output / "CURRENT.md").write_text(render_markdown(report), encoding="utf-8")

    manifest = report["manifest"]
    print(f"rows {manifest['row_count']:,}  regions {len(manifest['regions'])}")
    print(f"hash {manifest['dataset_hash'][:16]}…")
    print(f"written {args.output / 'CURRENT.md'}")


if __name__ == "__main__":
    main()
