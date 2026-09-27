"""Single-link clustering over geography, time and taxonomy fit.

Why single link rather than DBSCAN or HDBSCAN. An emerging city problem spreads
along a street or a pipe, so its reports form a chain rather than a ball, and
single link follows a chain. It is also deterministic and needs no numerical
library, which keeps the radar available on the CPU-only fallback path.

What this module refuses to do. It does not read appeal text, it does not name a
cause, and it does not promote anything. It reports that a group of reports
arrived together and fits the existing taxonomy poorly. A human decides what
that means.

Semantic similarity is a designed input that is not connected. No regional
export carries the citizen's own words (blocker B02), so the scan reports the
semantic signal as UNAVAILABLE rather than pretending that taxonomy codes are a
substitute for what people actually wrote.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from pulse109.capability import CapabilityStatus

from .models import (
    ALGORITHM_VERSION,
    ClusterMember,
    ClusterSignal,
    DiscoveryFeature,
    DiscoveryPolicy,
    DiscoveryReport,
    EmergingCluster,
)

_EARTH_RADIUS_M = 6_371_000.0
_MAX_SCAN = 5_000


def haversine_m(first: tuple[float, float], second: tuple[float, float]) -> float:
    """Great-circle distance in metres between (longitude, latitude) pairs."""
    lat1, lat2 = math.radians(first[1]), math.radians(second[1])
    delta_lat = lat2 - lat1
    delta_lon = math.radians(second[0] - first[0])
    inner = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(inner))


def _novelty(feature: DiscoveryFeature) -> float:
    """How poorly this report fits what the taxonomy already knows.

    A report routed with high confidence is familiar. One sent to manual review,
    or routed with low confidence, or carrying no topic at all, is the kind that
    an existing category may not cover yet.
    """
    if feature.manual_review:
        return 1.0
    if feature.topic_id is None:
        return 1.0
    if feature.routing_confidence is None:
        return 0.5
    return max(0.0, min(1.0, 1.0 - feature.routing_confidence))


def _pair_affinity(
    left: DiscoveryFeature, right: DiscoveryFeature, policy: DiscoveryPolicy
) -> tuple[float, list[str], set[ClusterSignal]]:
    """Weighted affinity in [0, 1], renormalised over the signals available.

    A pair with no coordinates is not penalised for it. The geo weight is simply
    removed from the denominator, so an unmeasurable signal never masquerades as
    a measured zero.
    """
    components: list[tuple[float, float, str, ClusterSignal]] = []

    if left.located and right.located:
        distance = haversine_m(
            (float(left.longitude or 0.0), float(left.latitude or 0.0)),
            (float(right.longitude or 0.0), float(right.latitude or 0.0)),
        )
        if distance > policy.max_geo_distance_m:
            return 0.0, [], set()
        components.append(
            (
                policy.weight_geo,
                1.0 - distance / policy.max_geo_distance_m,
                "GEO_PROXIMITY",
                ClusterSignal.GEO,
            )
        )

    if left.has_business_time and right.has_business_time:
        gap_minutes = abs((left.received_at - right.received_at).total_seconds()) / 60
        if gap_minutes > policy.max_time_gap_minutes:
            return 0.0, [], set()
        components.append(
            (
                policy.weight_time,
                1.0 - gap_minutes / policy.max_time_gap_minutes,
                "TIME_PROXIMITY",
                ClusterSignal.TIME,
            )
        )
    elif not (left.located and right.located):
        # One report has no business time, so the pair cannot be judged on when
        # it happened. Without a measured location either, nothing links them,
        # and inventing a timestamp from the moment of ingestion would be a lie
        # about the city rather than a gap in the data.
        return 0.0, [], set()

    if left.topic_id is not None and right.topic_id is not None:
        components.append(
            (
                policy.weight_taxonomy,
                1.0 if left.topic_id == right.topic_id else 0.0,
                "SAME_TOPIC" if left.topic_id == right.topic_id else "DIFFERENT_TOPIC",
                ClusterSignal.TAXONOMY,
            )
        )

    novelty = (_novelty(left) + _novelty(right)) / 2
    components.append((policy.weight_novelty, novelty, "LOW_TAXONOMY_FIT", ClusterSignal.NOVELTY))

    total_weight = sum(weight for weight, _, _, _ in components)
    if total_weight <= 0:
        return 0.0, [], set()
    score = sum(weight * value for weight, value, _, _ in components) / total_weight
    reasons = [reason for _, value, reason, _ in components if value > 0.0]
    signals = {signal for _, value, _, signal in components if value > 0.0}
    return score, reasons, signals


class EmergingIssueDetector:
    """Group reports that arrived together and fit the taxonomy poorly."""

    def __init__(self, policy: DiscoveryPolicy | None = None) -> None:
        self.policy = policy or DiscoveryPolicy()

    def scan(
        self,
        features: Sequence[DiscoveryFeature],
        *,
        region_id: str,
        window_hours: float,
        now: datetime | None = None,
        synthetic: bool = False,
    ) -> DiscoveryReport:
        policy = self.policy
        moment = now or datetime.now(timezone.utc)
        horizon = moment - timedelta(hours=window_hours)
        # A report without business time cannot be placed in the window, so it
        # enters the scan only on the observation the storage layer recorded and
        # is never allowed to link on time alone.
        scoped = [
            feature
            for feature in features
            if feature.region_id == region_id and feature.received_at >= horizon
        ][:_MAX_SCAN]

        semantic_status = CapabilityStatus.unavailable("CITIZEN_TEXT_ABSENT")
        if len(scoped) < policy.min_cluster_size:
            return DiscoveryReport(
                status=CapabilityStatus.abstained("WINDOW_BELOW_MINIMUM_SIZE"),
                semantic_status=semantic_status,
                scanned_appeals=len(scoped),
                window_hours=window_hours,
                policy=policy,
            )

        parent = list(range(len(scoped)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        affinities: dict[tuple[int, int], tuple[float, list[str], set[ClusterSignal]]] = {}
        for i in range(len(scoped)):
            for j in range(i + 1, len(scoped)):
                score, reasons, signals = _pair_affinity(scoped[i], scoped[j], policy)
                if score <= 0.0:
                    continue
                affinities[(i, j)] = (score, reasons, signals)
                if score >= policy.min_cohesion:
                    root_i, root_j = find(i), find(j)
                    if root_i != root_j:
                        parent[root_j] = root_i

        groups: dict[int, list[int]] = {}
        for index in range(len(scoped)):
            groups.setdefault(find(index), []).append(index)

        clusters: list[EmergingCluster] = []
        for members in groups.values():
            if len(members) < policy.min_cluster_size:
                continue
            cluster = self._assemble(scoped, members, affinities, region_id, synthetic)
            if cluster.cohesion_score < policy.min_cohesion:
                continue
            if cluster.novelty_score < policy.min_novelty:
                continue
            clusters.append(cluster)

        clusters.sort(key=lambda item: (-item.cluster_score, item.first_seen_at))
        status = (
            CapabilityStatus.available()
            if clusters
            else CapabilityStatus.abstained("NO_CLUSTER_ABOVE_THRESHOLD")
        )
        return DiscoveryReport(
            status=status,
            semantic_status=semantic_status,
            scanned_appeals=len(scoped),
            window_hours=window_hours,
            policy=policy,
            clusters=clusters[:100],
        )

    def _assemble(
        self,
        scoped: Sequence[DiscoveryFeature],
        members: Sequence[int],
        affinities: dict[tuple[int, int], tuple[float, list[str], set[ClusterSignal]]],
        region_id: str,
        synthetic: bool,
    ) -> EmergingCluster:
        features = [scoped[index] for index in members]
        times = [feature.received_at for feature in features]
        located = [
            (float(feature.longitude or 0.0), float(feature.latitude or 0.0))
            for feature in features
            if feature.located
        ]

        centroid: tuple[float, float] | None = None
        radius: float | None = None
        if located:
            centroid = (
                sum(point[0] for point in located) / len(located),
                sum(point[1] for point in located) / len(located),
            )
            radius = round(max(haversine_m(centroid, point) for point in located), 1)

        pair_scores: list[float] = []
        signals: set[ClusterSignal] = set()
        member_scores: dict[int, list[float]] = {index: [] for index in members}
        member_reasons: dict[int, set[str]] = {index: set() for index in members}
        ordered = sorted(members)
        for position, i in enumerate(ordered):
            for j in ordered[position + 1 :]:
                entry = affinities.get((i, j))
                if entry is None:
                    continue
                score, reasons, pair_signals = entry
                pair_scores.append(score)
                signals |= pair_signals
                member_scores[i].append(score)
                member_scores[j].append(score)
                member_reasons[i] |= set(reasons)
                member_reasons[j] |= set(reasons)

        cohesion = sum(pair_scores) / len(pair_scores) if pair_scores else 0.0
        novelty = sum(_novelty(feature) for feature in features) / len(features)
        topics = Counter(feature.topic_id for feature in features if feature.topic_id is not None)
        languages = Counter(
            feature.language for feature in features if feature.language is not None
        )

        # A cluster identity that survives a rescan of the same reports, so an
        # operator reviewing one does not find it renamed underneath them.
        fingerprint = ",".join(sorted(str(feature.request_id) for feature in features))
        cluster_id = uuid5(NAMESPACE_URL, f"pulse109-emerging-cluster:{region_id}:{fingerprint}")

        return EmergingCluster(
            cluster_id=cluster_id,
            region_id=region_id,
            state="open",
            first_seen_at=min(times),
            last_seen_at=max(times),
            appeal_count=len(features),
            centroid_longitude=centroid[0] if centroid else None,
            centroid_latitude=centroid[1] if centroid else None,
            radius_m=radius,
            cohesion_score=round(cohesion, 4),
            novelty_score=round(novelty, 4),
            cluster_score=round((cohesion + novelty) / 2, 4),
            signals_used=sorted(signals, key=lambda item: item.value),
            top_topics=[
                (topic, round(count / len(features), 4)) for topic, count in topics.most_common(10)
            ],
            languages=dict(languages),
            members_without_business_time=sum(
                1 for feature in features if not feature.has_business_time
            ),
            members=[
                ClusterMember(
                    request_id=scoped[index].request_id,
                    score=round(
                        sum(member_scores[index]) / len(member_scores[index])
                        if member_scores[index]
                        else 0.0,
                        4,
                    ),
                    membership_reasons=sorted(member_reasons[index])[:8],
                )
                for index in ordered
            ],
            algorithm_version=ALGORITHM_VERSION,
            synthetic=synthetic,
        )


__all__ = ["EmergingIssueDetector", "haversine_m"]
