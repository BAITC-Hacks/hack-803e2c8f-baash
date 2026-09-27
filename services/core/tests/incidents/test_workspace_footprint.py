"""The footprint must never let an empty map read as "no spread".

No regional export in this programme carries coordinates, so an incident with
zero located members is the ordinary case. The contract has to distinguish it
from an incident whose reports genuinely sit on one spot.
"""

from datetime import datetime, timezone
from uuid import uuid4

from pulse109.capability import CapabilityState
from pulse109.incidents.workspace import build_footprint
from pulse109.incidents.workspace_models import WorkspaceMember, WorkspacePoint


def member(longitude: float | None = None, latitude: float | None = None) -> WorkspaceMember:
    point = (
        WorkspacePoint(longitude=longitude, latitude=latitude)
        if longitude is not None and latitude is not None
        else None
    )
    return WorkspaceMember(
        request_id=uuid4(),
        source_request_id="demo-synthetic",
        membership="confirmed",
        status="new",
        received_at=datetime(2026, 9, 27, 10, 0, tzinfo=timezone.utc),
        received_at_quality="exact",
        language="ru",
        channel="web",
        point=point,
    )


def test_absent_coordinates_report_unavailable_not_empty() -> None:
    footprint = build_footprint([member(), member(), member()])
    assert footprint.status.state is CapabilityState.UNAVAILABLE
    assert footprint.status.reason_code == "COORDINATES_ABSENT"
    assert footprint.status.carries_information is False
    assert footprint.located_member_count == 0
    assert footprint.total_member_count == 3
    assert footprint.report_spread_m is None


def test_one_located_report_abstains_because_spread_means_nothing() -> None:
    footprint = build_footprint([member(76.9, 43.2), member()])
    assert footprint.status.state is CapabilityState.ABSTAINED
    assert footprint.status.reason_code == "SINGLE_LOCATED_REPORT"
    assert footprint.located_member_count == 1
    assert footprint.report_spread_m == 0.0


def test_spread_is_measured_from_the_centroid() -> None:
    # Two points about 1.6 km apart along a parallel at 43 degrees north.
    footprint = build_footprint([member(76.900, 43.200), member(76.920, 43.200)])
    assert footprint.status.state is CapabilityState.AVAILABLE
    assert footprint.located_member_count == 2
    assert footprint.centroid is not None
    assert round(footprint.centroid.longitude, 4) == 76.9100
    assert footprint.report_spread_m is not None
    assert 700 < footprint.report_spread_m < 900
    assert footprint.bounding_box == (76.900, 43.200, 76.920, 43.200)


def test_mixed_membership_counts_only_located_points() -> None:
    footprint = build_footprint([member(76.90, 43.20), member(76.91, 43.21), member(), member()])
    assert footprint.located_member_count == 2
    assert footprint.total_member_count == 4
    assert len(footprint.points) == 2
