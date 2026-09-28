"""Append-only Ask Pulse audit with hashes and controlled structured fields."""

from __future__ import annotations

from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from .errors import AnalyticsError


class PostgresAskAudit:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def __call__(self, entry: dict[str, object]) -> None:
        try:
            with psycopg.connect(self.database_url, connect_timeout=3) as connection:
                connection.execute(
                    "INSERT INTO analytics.ask_audit (query_id,actor_token,region_scope,"
                    "question_hash,locale,parser_version,intent,validated_query,status,"
                    "reason_code,data_cutoff,quality,records_considered) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        entry.get("query_id", str(uuid4())),
                        entry["actor_id"],
                        entry["region_id"],
                        entry["question_hash"],
                        entry["locale"],
                        entry["parser_version"],
                        Jsonb(entry.get("intent")),
                        Jsonb(entry.get("validated_query")),
                        entry["status"],
                        entry.get("reason_code"),
                        entry.get("data_cutoff"),
                        entry.get("quality"),
                        entry.get("records_considered") or 0,
                    ),
                )
        except psycopg.Error as error:
            raise AnalyticsError(
                "AUDIT_STORAGE_UNAVAILABLE", "Analytics audit is unavailable.", 503
            ) from error
