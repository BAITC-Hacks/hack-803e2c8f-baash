"""The EDA must be reproducible and must refuse to flatter the data.

Two properties matter more than any individual figure. The same file has to
produce the same report, or nobody can compare two runs. And a record whose
business time cannot be trusted must stay out of any chart that depends on the
hour, because putting it in a bucket nobody observed turns a plausible chart
into a false one.
"""

import json
from pathlib import Path

import pytest

from analytics.offline.manifest import build_manifest, read_canonical
from analytics.offline.quality import assess, weakest_dimensions
from analytics.offline.report import build_report, render_markdown
from analytics.offline.temporal import moving_average, profile


def record(
    *,
    region: str = "ALA",
    received: str | None = "2026-09-10T10:00:00+05:00",
    quality: str = "exact",
    channel: str | None = "phone",
    language: str | None = "ru",
    source_id: str = "R-1",
    status: str | None = "new",
    validation: str = "accepted",
) -> dict:
    return {
        "schema_version": "1.0.0",
        "source": {
            "region_id": region,
            "request_id": source_id,
            "source_record_checksum": "a" * 64,
            "system": "synthetic",
        },
        "intake": {"channel": channel, "language": language, "selected_attributes": {}},
        "time": {"received_at": received, "received_at_quality": quality},
        "execution": {"current_status": status},
        "ingestion": {
            "adapter_id": "synthetic-crm",
            "schema_mapping_version": "synthetic/1.0.0",
            "validation_status": validation,
            "warning_codes": [],
        },
    }


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    path = tmp_path / "canonical.jsonl"
    rows = [
        record(source_id="R-1"),
        record(source_id="R-2", received="2026-09-10T18:00:00+05:00"),
        record(source_id="R-3", received=None, quality="missing"),
        record(region="AST", source_id="R-4", channel=None, validation="warned"),
        record(region="AST", source_id="R-4"),
    ]
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8"
    )
    return path


def test_manifest_is_computed_from_the_file(dataset: Path) -> None:
    manifest, records = build_manifest(dataset, synthetic=True)
    assert manifest.row_count == 5
    assert manifest.regions == ("ALA", "AST")
    assert manifest.dataset_hash and len(manifest.dataset_hash) == 64
    assert manifest.synthetic is True
    assert len(records) == 5


def test_manifest_warns_that_regions_cover_different_periods(dataset: Path) -> None:
    manifest, _ = build_manifest(dataset, synthetic=True)
    assert any("different periods" in note for note in manifest.notes)


def test_manifest_states_that_citizen_text_is_absent(dataset: Path) -> None:
    manifest, _ = build_manifest(dataset, synthetic=True)
    assert any("citizen text" in note for note in manifest.notes)


def test_report_is_reproducible_for_the_same_file(dataset: Path) -> None:
    first = build_report(dataset, synthetic=True)
    second = build_report(dataset, synthetic=True)
    for section in ("quality", "temporal", "distributions"):
        assert first[section] == second[section]
    assert first["manifest"]["dataset_hash"] == second["manifest"]["dataset_hash"]


def test_untrusted_business_time_is_excluded_from_hour_charts(dataset: Path) -> None:
    _, records = build_manifest(dataset, synthetic=True)
    ala = next(item for item in profile(records) if item.region_id == "ALA")
    assert ala.total_rows == 3
    # The third ALA record has no business time and must not reach an hour bucket.
    assert ala.trusted_rows == 2
    assert sum(ala.hour_counts.values()) == 2


def test_a_duplicate_source_id_lowers_uniqueness(dataset: Path) -> None:
    _, records = build_manifest(dataset, synthetic=True)
    ast = next(item for item in assess(records) if item.region_id == "AST")
    assert ast.duplicate_source_ids == 1
    uniqueness = next(d for d in ast.dimensions if d.name == "uniqueness")
    assert uniqueness.ratio == 0.5


def test_a_warned_row_lowers_consistency(dataset: Path) -> None:
    _, records = build_manifest(dataset, synthetic=True)
    ast = next(item for item in assess(records) if item.region_id == "AST")
    consistency = next(d for d in ast.dimensions if d.name == "consistency")
    assert consistency.ratio == 0.5


def test_healthy_dimensions_are_not_listed_as_places_to_look(dataset: Path) -> None:
    _, records = build_manifest(dataset, synthetic=True)
    listed = weakest_dimensions(assess(records))
    assert listed
    assert all(ratio < 0.95 for _, _, ratio in listed)


def test_moving_average_treats_a_missing_day_as_zero() -> None:
    series = moving_average({"2026-09-01": 10, "2026-09-03": 10}, window=3)
    assert [day for day, _ in series] == ["2026-09-01", "2026-09-02", "2026-09-03"]
    assert series[-1][1] == pytest.approx(20 / 3, abs=0.01)


def test_markdown_states_the_limits_and_the_synthetic_label(dataset: Path) -> None:
    text = render_markdown(build_report(dataset, synthetic=True))
    assert "This dataset is synthetic" in text
    assert "Nothing here establishes cause" in text.replace("\n", " ")
    assert "## Limits" in text


def test_a_malformed_line_is_reported_not_skipped(tmp_path: Path) -> None:
    path = tmp_path / "broken.jsonl"
    path.write_text('{"schema_version": "1.0.0"}\nnot json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        list(read_canonical(path))
