from datetime import datetime, timedelta, timezone

import pytest
from pulse109.replay import ReplayCase, ReplayDataset, ReplayEngine, ReplayLabel, snapshot_sha256
from pydantic import ValidationError

DECISION_AT = datetime(2026, 8, 1, 12, tzinfo=timezone.utc)


class RouteBySignal:
    def __init__(self, version: str, expected: str) -> None:
        self.policy_id = "routing"
        self.version = version
        self.region_id = "ALA"
        self.expected = expected
        self.seen: list[dict[str, object]] = []

    def predict(self, features: dict[str, object]) -> str:
        self.seen.append(features)
        assert "confirmed_route" not in features
        assert "case_key" not in features
        assert "decision_at" not in features
        return self.expected


def _case(key: str, *, synthetic: bool = False, route: str | None = "water") -> ReplayCase:
    return ReplayCase(
        case_key=key * 64,
        region_id="ALA",
        decision_at=DECISION_AT,
        features={"channel": {"value": "web", "observed_at": DECISION_AT - timedelta(hours=1)}},
        label=(
            ReplayLabel(
                confirmed_route=route,
                handoff_count=1,
                label_observed_at=DECISION_AT + timedelta(days=1),
            )
            if route is not None
            else None
        ),
        is_synthetic=synthetic,
    )


def _dataset(cases: tuple[ReplayCase, ...]) -> ReplayDataset:
    dataset = ReplayDataset(
        dataset_id="immutable-2026-08",
        region_id="ALA",
        snapshot_sha256="a" * 64,
        schema_version="replay-snapshot-v1",
        cases=cases,
        allowed_features=frozenset({"channel"}),
        cutoff_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    return dataset.model_copy(update={"snapshot_sha256": snapshot_sha256(dataset)})


def test_replay_is_deterministic_excludes_synthetic_and_never_promotes() -> None:
    dataset = _dataset((_case("b"), _case("a"), _case("c", synthetic=True)))
    baseline = RouteBySignal("v1", "water")
    candidate = RouteBySignal("v2", "roads")

    report = ReplayEngine().compare(dataset, baseline, candidate)
    repeated = ReplayEngine().compare(
        dataset, RouteBySignal("v1", "water"), RouteBySignal("v2", "roads")
    )

    assert report == repeated
    assert report.baseline.evaluated_count == 2
    assert report.candidate.evaluated_count == 2
    assert report.baseline.synthetic_count == report.candidate.synthetic_count == 1
    assert report.baseline.confirmed_route_agreement == 1.0
    assert report.candidate.confirmed_route_agreement == 0.0
    assert report.candidate.route_change_count == 2
    assert report.promoted is False
    assert baseline.seen == [{"channel": "web"}, {"channel": "web"}]


def test_synthetic_only_dataset_never_reports_model_quality() -> None:
    report = ReplayEngine().compare(
        _dataset((_case("a", synthetic=True),)),
        RouteBySignal("v1", "water"),
        RouteBySignal("v2", "water"),
    )
    assert report.baseline.evaluated_count == 0
    assert report.baseline.synthetic_count == 1
    assert report.baseline.confirmed_route_agreement is None


def test_dataset_manifest_is_independent_of_input_file_order() -> None:
    assert (
        _dataset((_case("a"), _case("b"))).manifest_digest()
        == _dataset((_case("b"), _case("a"))).manifest_digest()
    )


def test_rejects_post_decision_feature_and_pre_decision_outcome() -> None:
    with pytest.raises(ValidationError, match="post-decision"):
        ReplayCase(
            case_key="a" * 64,
            region_id="ALA",
            decision_at=DECISION_AT,
            features={
                "operator_override": {
                    "value": True,
                    "observed_at": DECISION_AT + timedelta(seconds=1),
                }
            },
        )
    with pytest.raises(ValidationError, match="predates the decision"):
        ReplayCase(
            case_key="a" * 64,
            region_id="ALA",
            decision_at=DECISION_AT,
            features={},
            label=ReplayLabel(
                confirmed_route="water",
                label_observed_at=DECISION_AT - timedelta(seconds=1),
            ),
        )


def test_rejects_unknown_feature_and_same_policy_version() -> None:
    with pytest.raises(ValidationError, match="allowed_features"):
        ReplayDataset(
            dataset_id="d",
            region_id="ALA",
            snapshot_sha256="a" * 64,
            schema_version="v1",
            cases=(_case("a"),),
            allowed_features=frozenset(),
            cutoff_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
    policy = RouteBySignal("v1", "water")
    with pytest.raises(ValueError, match="distinct approved versions"):
        ReplayEngine().compare(_dataset((_case("a"),)), policy, policy)


def test_rejects_cross_region_policy_and_sensitive_feature_name() -> None:
    candidate = RouteBySignal("v2", "water")
    candidate.region_id = "OTHER"
    with pytest.raises(ValueError, match="share a region"):
        ReplayEngine().compare(_dataset((_case("a"),)), RouteBySignal("v1", "water"), candidate)
    with pytest.raises(ValidationError, match="unapproved feature names"):
        ReplayDataset(
            dataset_id="sensitive",
            region_id="ALA",
            snapshot_sha256="a" * 64,
            schema_version="v1",
            cases=(_case("a"),),
            allowed_features=frozenset({"channel", "citizen_token"}),
            cutoff_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )


def test_rejects_free_text_policy_output() -> None:
    with pytest.raises(ValueError, match="canonical route code"):
        ReplayEngine().compare(
            _dataset((_case("a"),)),
            RouteBySignal("v1", "water outage at 555-123-4567"),
            RouteBySignal("v2", "water"),
        )


def test_language_slices_and_operator_rates() -> None:
    case_kk = ReplayCase(
        case_key="1" * 64,
        region_id="ALA",
        decision_at=DECISION_AT,
        features={
            "channel": {"value": "web", "observed_at": DECISION_AT},
            "language": {"value": "kk", "observed_at": DECISION_AT},
        },
        label=ReplayLabel(
            confirmed_route="water",
            handoff_count=0,
            label_observed_at=DECISION_AT + timedelta(days=1),
        ),
        is_synthetic=False,
    )
    case_ru = ReplayCase(
        case_key="2" * 64,
        region_id="ALA",
        decision_at=DECISION_AT,
        features={
            "channel": {"value": "web", "observed_at": DECISION_AT},
            "language": {"value": "ru", "observed_at": DECISION_AT},
        },
        label=ReplayLabel(
            confirmed_route="roads",
            handoff_count=1,
            label_observed_at=DECISION_AT + timedelta(days=1),
        ),
        is_synthetic=False,
    )
    dataset = ReplayDataset(
        dataset_id="slices-test",
        region_id="ALA",
        snapshot_sha256="b" * 64,
        schema_version="v1",
        cases=(case_kk, case_ru),
        allowed_features=frozenset({"channel", "language"}),
        cutoff_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    dataset = dataset.model_copy(update={"snapshot_sha256": snapshot_sha256(dataset)})

    baseline = RouteBySignal("v1", "water")
    candidate = RouteBySignal("v2", "roads")

    report = ReplayEngine().compare(dataset, baseline, candidate)

    # Baseline: matched kk ("water"), missed ru ("roads")
    assert report.baseline.language_slice_agreement["kk"] == 1.0
    assert report.baseline.language_slice_agreement["ru"] == 0.0
    assert report.baseline.confirmed_route_agreement == 0.5
    assert report.baseline.operator_override_rate == 0.5

    # Candidate: missed kk, matched ru
    assert report.candidate.language_slice_agreement["kk"] == 0.0
    assert report.candidate.language_slice_agreement["ru"] == 1.0
    assert report.candidate.confirmed_route_agreement == 0.5
    assert report.candidate.operator_override_rate == 0.5
