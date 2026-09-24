"""Region-scoped approved confidence policy resolution for Decision Gateway."""

from __future__ import annotations

import math
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Protocol

import psycopg
from psycopg.rows import dict_row

from .gateway import EffectiveConfidencePolicy


class ConfidencePolicyConflict(RuntimeError):
    """Effective policy data is ambiguous or malformed; evaluation must fail closed."""


class ConfidencePolicyRepository(Protocol):
    def resolve(
        self,
        *,
        region_id: str,
        artifact_sha256: str,
        taxonomy_version: str,
        preprocess_version: str,
        at: datetime,
        allow_synthetic: bool = False,
    ) -> EffectiveConfidencePolicy | None: ...


class PostgresConfidencePolicyRepository:
    """Read exactly one approved policy for a region and business timestamp."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            yield connection

    def resolve(
        self,
        *,
        region_id: str,
        artifact_sha256: str,
        taxonomy_version: str,
        preprocess_version: str,
        at: datetime,
        allow_synthetic: bool = False,
    ) -> EffectiveConfidencePolicy | None:
        if (
            re.fullmatch(r"[A-Z0-9_-]{2,32}", region_id) is None
            or re.fullmatch(r"[a-f0-9]{64}", artifact_sha256) is None
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}", taxonomy_version) is None
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}", preprocess_version) is None
            or at.tzinfo is None
            or at.utcoffset() is None
        ):
            raise ValueError(
                "bounded region, artifact, taxonomy, preprocessing and aware timestamp are required"
            )
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT version, high_min, medium_min, abstain_below
                FROM triage.confidence_policy_version
                WHERE region_id = %s AND artifact_sha256 = %s
                  AND taxonomy_version = %s AND preprocess_version = %s
                  AND state = 'approved'
                  AND effective_from <= %s
                  AND (effective_to IS NULL OR effective_to > %s)
                  AND (%s OR NOT synthetic_only)
                ORDER BY effective_from DESC, policy_id
                LIMIT 2
                """,
                (
                    region_id,
                    artifact_sha256,
                    taxonomy_version,
                    preprocess_version,
                    at,
                    at,
                    allow_synthetic,
                ),
            )
            rows = cursor.fetchall()
        if not rows:
            return None
        if len(rows) != 1:
            raise ConfidencePolicyConflict("multiple approved confidence policies are effective")
        row = rows[0]
        try:
            values = tuple(float(row[key]) for key in ("high_min", "medium_min", "abstain_below"))
            version = row["version"]
            if not isinstance(version, str) or not version.strip():
                raise ValueError("empty policy version")
            if not all(math.isfinite(value) and 0 <= value <= 1 for value in values):
                raise ValueError("threshold outside finite unit interval")
            high_min, medium_min, abstain_below = values
            if high_min < medium_min or medium_min < abstain_below:
                raise ValueError("thresholds are not ordered")
            return EffectiveConfidencePolicy(
                version=version,
                approved=True,
                artifact_sha256=artifact_sha256,
                taxonomy_version=taxonomy_version,
                preprocess_version=preprocess_version,
                high_min=high_min,
                medium_min=medium_min,
                abstain_below=abstain_below,
            )
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ConfidencePolicyConflict("approved confidence policy is malformed") from exc
