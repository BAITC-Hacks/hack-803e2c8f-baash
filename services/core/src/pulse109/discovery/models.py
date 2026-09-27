"""Contracts for emerging problem discovery.

A city problem can arrive before a category exists for it. The radar looks for
groups of reports that arrive close together in space and time and fit the
existing taxonomy poorly. It says a pattern appeared. It never says what caused
it, because it has no way to know that.

Everything here is presence and geometry. No appeal text crosses this boundary,
so the module can run without a privacy exemption.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pulse109.capability import CapabilityStatus

ALGORITHM_VERSION = "discovery-geo-time-taxonomy-1.0.0"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClusterSignal(str, Enum):
    """Which components contributed to a cluster score."""

    GEO = "geo"
    TIME = "time"
    TAXONOMY = "taxonomy"
    NOVELTY = "novelty"
    SEMANTIC = "semantic"


class DiscoveryPolicy(StrictModel):
    """Thresholds are configuration, never business truth compiled into code.

    A supervisor has to be able to make the radar quieter or louder without a
    release, and a reviewer has to see exactly what produced an alert.
    """

    max_geo_distance_m: float = Field(default=1500.0, gt=0.0, le=50_000.0)
    max_time_gap_minutes: float = Field(default=120.0, gt=0.0, le=10_080.0)
    min_cluster_size: int = Field(default=3, ge=2, le=1000)
    min_cohesion: float = Field(default=0.35, ge=0.0, le=1.0)
    min_novelty: float = Field(default=0.30, ge=0.0, le=1.0)
    # Novelty is deliberately absent from these weights. It describes one report,
    # not the relationship between two, so letting it link a pair makes any two
    # unusual reports look related. It gates the cluster instead, through
    # min_novelty.
    weight_geo: float = Field(default=0.45, ge=0.0, le=1.0)
    weight_time: float = Field(default=0.30, ge=0.0, le=1.0)
    weight_taxonomy: float = Field(default=0.25, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_weights(self) -> DiscoveryPolicy:
        total = self.weight_geo + self.weight_time + self.weight_taxonomy
        if not 0.99 <= total <= 1.01:
            raise ValueError("affinity weights must sum to one")
        return self


class DiscoveryFeature(StrictModel):
    """One appeal reduced to the signals the radar is allowed to see."""

    request_id: UUID
    region_id: str = Field(pattern=r"^[A-Z0-9_-]{2,32}$")
    received_at: datetime
    # An appeal whose business time is missing was observed, not reported, at this
    # moment. Treating the two as the same invents a timestamp, which the project
    # invariants forbid, so the quality travels with the value.
    time_quality: Literal["exact", "source_tz_assumed", "date_only", "missing"] = "exact"
    topic_id: str | None = None
    service_id: str | None = None
    language: str | None = None
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    routing_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    manual_review: bool = False

    @model_validator(mode="after")
    def validate_point(self) -> DiscoveryFeature:
        if (self.longitude is None) != (self.latitude is None):
            raise ValueError("a point needs both longitude and latitude")
        return self

    @property
    def located(self) -> bool:
        return self.longitude is not None and self.latitude is not None

    @property
    def has_business_time(self) -> bool:
        return self.time_quality != "missing"


class ClusterMember(StrictModel):
    request_id: UUID
    score: float = Field(ge=0.0, le=1.0)
    membership_reasons: list[str] = Field(default_factory=list, max_length=8)


class EmergingCluster(StrictModel):
    """A group of reports that arrived together and fits the taxonomy poorly."""

    cluster_id: UUID
    region_id: str
    state: Literal["open", "under_review", "promoted", "dismissed", "known_pattern"]
    first_seen_at: datetime
    last_seen_at: datetime
    appeal_count: int = Field(ge=0)
    centroid_longitude: float | None = None
    centroid_latitude: float | None = None
    radius_m: float | None = Field(default=None, ge=0.0)
    cohesion_score: float = Field(ge=0.0, le=1.0)
    novelty_score: float = Field(ge=0.0, le=1.0)
    cluster_score: float = Field(ge=0.0, le=1.0)
    signals_used: list[ClusterSignal] = Field(default_factory=list)
    top_topics: list[tuple[str, float]] = Field(default_factory=list, max_length=10)
    languages: dict[str, int] = Field(default_factory=dict)
    members: list[ClusterMember] = Field(default_factory=list, max_length=1000)
    members_without_business_time: int = Field(default=0, ge=0)
    algorithm_version: str = ALGORITHM_VERSION
    synthetic: bool = False
    # The radar reports that a pattern appeared. Naming a cause is a human act.
    advisory_only: Literal[True] = True

    @property
    def active_minutes(self) -> float:
        return round((self.last_seen_at - self.first_seen_at).total_seconds() / 60, 1)


class DiscoveryReport(StrictModel):
    """What one scan found, and which signals were actually available to it."""

    status: CapabilityStatus
    semantic_status: CapabilityStatus
    scanned_appeals: int = Field(ge=0)
    window_hours: float = Field(gt=0.0)
    policy: DiscoveryPolicy
    clusters: list[EmergingCluster] = Field(default_factory=list, max_length=100)
    algorithm_version: str = ALGORITHM_VERSION


class ClusterReview(StrictModel):
    """A human decision about a cluster. The radar never promotes on its own."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["promote", "dismiss", "known_pattern", "under_review"]
    reason_code: str = Field(min_length=1, max_length=128, pattern=r"^[A-Z][A-Z0-9_]{0,127}$")
    note: str | None = Field(default=None, max_length=1000)
