"""The radar must find a real chain and stay quiet about ordinary traffic.

The failure that matters here is a false alert. A supervisor who learns that the
radar cries wolf will stop reading it, and the feature is then worse than absent.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pulse109.capability import CapabilityState
from pulse109.discovery.models import ClusterSignal, DiscoveryFeature, DiscoveryPolicy
from pulse109.discovery.service import EmergingIssueDetector, haversine_m

BASE = datetime(2026, 9, 27, 10, 0, tzinfo=timezone.utc)


def feature(
    *,
    minutes: float = 0.0,
    longitude: float | None = 76.890,
    latitude: float | None = 43.238,
    topic: str | None = "topic:water",
    confidence: float | None = 0.3,
    manual_review: bool = False,
    language: str = "ru",
) -> DiscoveryFeature:
    return DiscoveryFeature(
        request_id=uuid4(),
        region_id="ALA",
        received_at=BASE + timedelta(minutes=minutes),
        topic_id=topic,
        service_id="service:water",
        language=language,
        longitude=longitude,
        latitude=latitude,
        routing_confidence=confidence,
        manual_review=manual_review,
    )


def test_a_tight_low_confidence_chain_becomes_a_cluster() -> None:
    features = [
        feature(minutes=0, longitude=76.8900, latitude=43.2380),
        feature(minutes=7, longitude=76.8912, latitude=43.2384, language="kk"),
        feature(minutes=15, longitude=76.8925, latitude=43.2389),
        feature(minutes=22, longitude=76.8938, latitude=43.2393, language="kk"),
    ]
    report = EmergingIssueDetector().scan(
        features, region_id="ALA", window_hours=6, now=BASE + timedelta(hours=1)
    )
    assert report.status.state is CapabilityState.AVAILABLE
    assert len(report.clusters) == 1
    cluster = report.clusters[0]
    assert cluster.appeal_count == 4
    assert cluster.radius_m is not None and cluster.radius_m < 400
    assert cluster.languages == {"ru": 2, "kk": 2}
    assert ClusterSignal.GEO in cluster.signals_used
    assert cluster.active_minutes == 22.0
    assert cluster.advisory_only is True


def test_confidently_routed_traffic_raises_no_alert() -> None:
    """Routine reports are familiar by definition and must not trip the radar."""
    features = [
        feature(minutes=index * 5, longitude=76.89 + index * 0.001, confidence=0.97)
        for index in range(6)
    ]
    report = EmergingIssueDetector().scan(
        features, region_id="ALA", window_hours=6, now=BASE + timedelta(hours=1)
    )
    assert report.status.state is CapabilityState.ABSTAINED
    assert report.status.reason_code == "NO_CLUSTER_ABOVE_THRESHOLD"
    assert report.clusters == []


def test_reports_far_apart_do_not_join() -> None:
    near = [feature(minutes=index * 4, longitude=76.890 + index * 0.001) for index in range(3)]
    far = [feature(minutes=index * 4, longitude=77.400 + index * 0.001) for index in range(3)]
    report = EmergingIssueDetector().scan(
        near + far, region_id="ALA", window_hours=6, now=BASE + timedelta(hours=1)
    )
    assert len(report.clusters) == 2
    for cluster in report.clusters:
        assert cluster.appeal_count == 3


def test_semantic_signal_is_reported_unavailable_not_silently_skipped() -> None:
    report = EmergingIssueDetector().scan(
        [feature(minutes=index * 3) for index in range(4)],
        region_id="ALA",
        window_hours=6,
        now=BASE + timedelta(hours=1),
    )
    assert report.semantic_status.state is CapabilityState.UNAVAILABLE
    assert report.semantic_status.reason_code == "CITIZEN_TEXT_ABSENT"


def test_missing_coordinates_do_not_block_clustering() -> None:
    """Geography is one signal. Without it the rest must still be usable."""
    features = [
        feature(minutes=index * 6, longitude=None, latitude=None, manual_review=True)
        for index in range(4)
    ]
    report = EmergingIssueDetector().scan(
        features, region_id="ALA", window_hours=6, now=BASE + timedelta(hours=1)
    )
    assert report.status.state is CapabilityState.AVAILABLE
    cluster = report.clusters[0]
    assert cluster.radius_m is None
    assert cluster.centroid_longitude is None
    assert ClusterSignal.GEO not in cluster.signals_used


def test_a_thin_window_abstains_instead_of_guessing() -> None:
    report = EmergingIssueDetector().scan(
        [feature(minutes=0), feature(minutes=2)],
        region_id="ALA",
        window_hours=6,
        now=BASE + timedelta(hours=1),
    )
    assert report.status.state is CapabilityState.ABSTAINED
    assert report.status.reason_code == "WINDOW_BELOW_MINIMUM_SIZE"


def test_cluster_identity_survives_a_rescan() -> None:
    features = [feature(minutes=index * 5) for index in range(4)]
    detector = EmergingIssueDetector()
    first = detector.scan(features, region_id="ALA", window_hours=6, now=BASE + timedelta(hours=1))
    second = detector.scan(
        list(reversed(features)), region_id="ALA", window_hours=6, now=BASE + timedelta(hours=1)
    )
    assert first.clusters[0].cluster_id == second.clusters[0].cluster_id


def test_thresholds_are_policy_and_change_the_outcome() -> None:
    features = [feature(minutes=index * 5, confidence=0.8) for index in range(4)]
    strict = EmergingIssueDetector().scan(
        features, region_id="ALA", window_hours=6, now=BASE + timedelta(hours=1)
    )
    assert strict.clusters == []
    lenient = EmergingIssueDetector(DiscoveryPolicy(min_novelty=0.1, min_cohesion=0.2)).scan(
        features, region_id="ALA", window_hours=6, now=BASE + timedelta(hours=1)
    )
    assert len(lenient.clusters) == 1


def test_haversine_matches_a_known_distance() -> None:
    # One degree of longitude at the equator is about 111.3 km.
    assert 111_000 < haversine_m((0.0, 0.0), (1.0, 0.0)) < 111_600


def test_a_report_without_business_time_never_links_on_time_alone() -> None:
    """Found by running the radar on the demo data.

    An appeal whose business time is missing was stored with the moment it was
    observed. Clustering on that value would place a report in a window it was
    never known to belong to, which is precisely the invented timestamp the
    project forbids.
    """
    timed = [feature(minutes=index * 5, longitude=None, latitude=None) for index in range(3)]
    untimed = DiscoveryFeature(
        request_id=uuid4(),
        region_id="ALA",
        received_at=BASE + timedelta(minutes=6),
        time_quality="missing",
        topic_id="topic:lighting",
        service_id="service:municipal",
        language="kk",
        longitude=None,
        latitude=None,
        routing_confidence=None,
        manual_review=True,
    )
    report = EmergingIssueDetector().scan(
        [*timed, untimed], region_id="ALA", window_hours=6, now=BASE + timedelta(hours=1)
    )
    joined = {member.request_id for cluster in report.clusters for member in cluster.members}
    assert untimed.request_id not in joined


def test_a_located_report_without_business_time_may_still_join_on_geography() -> None:
    """Geography is measured. Time is not, so only the measured signal counts."""
    timed = [
        feature(minutes=index * 5, longitude=76.8900 + index * 0.001, latitude=43.2380)
        for index in range(3)
    ]
    untimed = DiscoveryFeature(
        request_id=uuid4(),
        region_id="ALA",
        received_at=BASE + timedelta(minutes=6),
        time_quality="missing",
        topic_id="topic:water",
        service_id="service:water",
        language="ru",
        longitude=76.8905,
        latitude=43.2382,
        routing_confidence=None,
        manual_review=True,
    )
    report = EmergingIssueDetector().scan(
        [*timed, untimed], region_id="ALA", window_hours=6, now=BASE + timedelta(hours=1)
    )
    cluster = report.clusters[0]
    assert untimed.request_id in {member.request_id for member in cluster.members}
    assert cluster.members_without_business_time == 1
