"""Emerging issue radar endpoints.

A scan is a read that may persist what it found. Promotion to an incident is a
separate human act on the incident endpoints, so nothing here can create work on
its own.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status

from pulse109.security import AuthenticatedActor

from .models import ClusterReview, DiscoveryPolicy, DiscoveryReport
from .repository import DiscoveryRepository
from .service import EmergingIssueDetector


def create_discovery_router(
    repository: DiscoveryRepository,
    *,
    policy: DiscoveryPolicy | None = None,
    synthetic: bool = False,
    enabled: bool = True,
) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["Discovery"])
    detector = EmergingIssueDetector(policy)

    def _require_enabled() -> None:
        if not enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "discovery_unavailable",
                    "message": "Emerging issue discovery needs the PostgreSQL profile.",
                },
            )

    @router.post(
        "/discovery/scans",
        response_model=DiscoveryReport,
        operation_id="scanEmergingIssues",
    )
    def scan(
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        window_hours: float = Query(default=6.0, gt=0.0, le=336.0),
        persist: bool = Query(default=True),
    ) -> DiscoveryReport:
        identity.require_any_role("operator", "supervisor", "analyst", "admin")
        identity.require_region(region_id)
        _require_enabled()
        features = repository.read_features(
            region_id=region_id, window_hours=window_hours, now=datetime.now(timezone.utc)
        )
        report = detector.scan(
            features, region_id=region_id, window_hours=window_hours, synthetic=synthetic
        )
        if persist and report.clusters:
            repository.save_clusters(report.clusters, policy=report.policy)
        return report

    @router.get(
        "/discovery/clusters",
        operation_id="listEmergingClusters",
    )
    def list_clusters(
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> list[dict[str, Any]]:
        identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
        identity.require_region(region_id)
        _require_enabled()
        return repository.list_clusters(region_id=region_id, limit=limit)

    @router.get(
        "/discovery/clusters/{cluster_id}",
        operation_id="getEmergingCluster",
    )
    def get_cluster(
        cluster_id: UUID,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
    ) -> dict[str, Any]:
        identity.require_any_role("operator", "supervisor", "analyst", "auditor", "admin")
        identity.require_region(region_id)
        _require_enabled()
        cluster = repository.get_cluster(cluster_id, region_id=region_id)
        if cluster is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "cluster_not_found", "message": "No such cluster in this region."},
            )
        return cluster

    @router.post(
        "/discovery/clusters/{cluster_id}/reviews",
        operation_id="reviewEmergingCluster",
    )
    def review_cluster(
        cluster_id: UUID,
        review: ClusterReview,
        identity: AuthenticatedActor,
        region_id: str = Header(alias="X-Region-Id", pattern=r"^[A-Z0-9_-]{2,32}$"),
        promoted_incident_id: Annotated[UUID | None, Query()] = None,
    ) -> dict[str, Any]:
        """Record what a human decided about a cluster.

        Promotion records the incident a human created on the incident endpoints.
        This route never creates one, so the radar cannot open work by itself.
        """
        identity.require_any_role("operator", "supervisor", "admin")
        identity.require_region(region_id)
        _require_enabled()
        if review.decision == "promote" and promoted_incident_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "promotion_needs_incident",
                    "message": "Create the incident first, then record its id here.",
                },
            )
        updated = repository.review_cluster(
            cluster_id,
            region_id=region_id,
            review=review,
            actor_token=identity.actor_id,
            promoted_incident_id=promoted_incident_id,
        )
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "cluster_not_found", "message": "No such cluster in this region."},
            )
        return updated

    return router


__all__ = ["create_discovery_router"]
