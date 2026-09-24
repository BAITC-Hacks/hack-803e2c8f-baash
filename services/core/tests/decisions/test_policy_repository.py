from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

import pytest
from pulse109.decisions.gateway import EffectiveConfidencePolicy
from pulse109.decisions.policy_repository import (
    ConfidencePolicyConflict,
    PostgresConfidencePolicyRepository,
)


class _Cursor:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, *_: object) -> None:
        return None

    def fetchall(self) -> list[dict[str, object]]:
        return self.rows


class _Connection:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._cursor = _Cursor(rows)

    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def cursor(self) -> _Cursor:
        return self._cursor


def _row(**overrides: object) -> dict[str, object]:
    return {
        "version": "confidence-v1",
        "high_min": 0.8,
        "medium_min": 0.55,
        "abstain_below": 0.35,
        "artifact_sha256": "a" * 64,
        "taxonomy_version": "taxonomy-v1",
        "preprocess_version": "prep-v1",
        **overrides,
    }


def _repository(
    monkeypatch: pytest.MonkeyPatch, rows: list[dict[str, object]]
) -> PostgresConfidencePolicyRepository:
    repository = PostgresConfidencePolicyRepository("postgresql://unused")

    @contextmanager
    def connection():
        yield _Connection(rows)

    monkeypatch.setattr(repository, "_connection", connection)
    return repository


def _resolve(repository: PostgresConfidencePolicyRepository, **overrides: object):
    keys: dict[str, object] = {
        "region_id": "ALA",
        "artifact_sha256": "a" * 64,
        "taxonomy_version": "taxonomy-v1",
        "preprocess_version": "prep-v1",
        "at": datetime(2026, 9, 24, tzinfo=timezone.utc),
    }
    keys.update(overrides)
    return repository.resolve(**keys)  # type: ignore[arg-type]


def test_resolves_only_a_single_approved_effective_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = _resolve(_repository(monkeypatch, [_row()]))

    assert policy == EffectiveConfidencePolicy(
        version="confidence-v1",
        approved=True,
        artifact_sha256="a" * 64,
        taxonomy_version="taxonomy-v1",
        preprocess_version="prep-v1",
        high_min=0.8,
        medium_min=0.55,
        abstain_below=0.35,
    )


def test_missing_policy_fails_closed_as_none(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _resolve(_repository(monkeypatch, [])) is None


def test_overlap_and_malformed_thresholds_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = _repository(monkeypatch, [_row(), _row(version="confidence-v2")])
    with pytest.raises(ConfidencePolicyConflict):
        _resolve(repository)

    repository = _repository(monkeypatch, [_row(high_min=float("nan"))])
    with pytest.raises(ConfidencePolicyConflict):
        _resolve(repository)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("region_id", " "),
        ("region_id", "ala"),
        ("artifact_sha256", "z" * 64),
        ("taxonomy_version", "x" * 65),
        ("preprocess_version", " "),
        ("at", datetime(2026, 9, 24)),
    ],
)
def test_requires_region_and_timezone_aware_timestamp(
    monkeypatch: pytest.MonkeyPatch, key: str, value: object
) -> None:
    repository = _repository(monkeypatch, [])
    with pytest.raises(ValueError):
        _resolve(repository, **{key: value})
