"""Effective-dated policy reads with an explicit synthetic local profile."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .models import PolicyDefinition


def _psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


class PolicyService:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url

    def list_policies(
        self, *, region_id: str, effective_at: datetime, include_drafts: bool = False
    ) -> list[PolicyDefinition]:
        if self.database_url is None:
            return self._synthetic(region_id, effective_at, include_drafts)
        with psycopg.connect(_psycopg_url(self.database_url), row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT policy_type, region_id, version, state, effective_from,
                           effective_to, parameters, approval_ref, rollback_version,
                           synthetic_only
                    FROM catalog.policy_version
                    WHERE region_id = %s
                      AND (%s OR state = 'approved')
                      AND (state <> 'approved' OR effective_from <= %s)
                      AND (effective_to IS NULL OR effective_to > %s)
                    ORDER BY policy_type, version
                    """,
                    (region_id, include_drafts, effective_at, effective_at),
                )
                return [self._from_row(row) for row in cursor.fetchall()]

    @staticmethod
    def _from_row(row: dict[str, Any]) -> PolicyDefinition:
        parameters = row["parameters"]
        if isinstance(parameters, str):
            parameters = json.loads(parameters)
        return PolicyDefinition(
            policy_type=row["policy_type"],
            region_id=row["region_id"],
            version=row["version"],
            state=row["state"],
            effective_from=row["effective_from"],
            effective_to=row["effective_to"],
            parameters=parameters,
            approval_ref=row["approval_ref"],
            rollback_version=row["rollback_version"],
            synthetic_only=row["synthetic_only"],
        )

    @staticmethod
    def _synthetic(
        region_id: str, effective_at: datetime, include_drafts: bool
    ) -> list[PolicyDefinition]:
        effective_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        if effective_at < effective_from and not include_drafts:
            return []

        def policy(
            policy_type: str, version: str, parameters: dict[str, object]
        ) -> PolicyDefinition:
            return PolicyDefinition.model_validate(
                {
                    "policy_type": policy_type,
                    "region_id": region_id,
                    "version": version,
                    "state": "approved",
                    "effective_from": effective_from,
                    "approval_ref": "synthetic://approval/demo-only",
                    "rollback_version": None,
                    "synthetic_only": True,
                    "parameters": parameters,
                }
            )

        return [
            policy(
                "routing",
                "synthetic-routing-1.0.0",
                {"human_confirmation_required": True, "top_k": 3},
            ),
            policy(
                "confidence",
                "synthetic-confidence-1.0.0",
                {"high_min": 0.8, "medium_min": 0.55, "abstain_below": 0.35},
            ),
            policy(
                "sla",
                "synthetic-sla-unavailable-1.0.0",
                {"calculation_enabled": False, "reason": "policy_not_approved"},
            ),
        ]
