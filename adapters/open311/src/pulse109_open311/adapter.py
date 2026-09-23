"""Open311-shaped sandbox; it is not a live regional integration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import cast
from uuid import uuid4

from pulse109_adapter import (
    AdapterHealth,
    AdapterResult,
    AssignmentCommand,
    LifecycleStatus,
    PermanentAdapterError,
    RemoteStatusEvent,
    StatusMapping,
)


class Open311SyntheticAdapter:
    adapter_id = "open311-synthetic"

    def __init__(self) -> None:
        self.requests: dict[str, dict[str, object]] = {}
        self.commands: dict[str, AdapterResult] = {}

    def health(self) -> AdapterHealth:
        return AdapterHealth(self.adapter_id, True, 0, "synthetic://open311/checkpoint")

    def create_or_import(self, command_id: str, payload: dict[str, object]) -> AdapterResult:
        prior = self.commands.get(command_id)
        if prior is not None:
            return prior
        service_code = payload.get("service_code") or payload.get("service_id")
        description = payload.get("description")
        if not isinstance(service_code, str) or not isinstance(description, str):
            raise PermanentAdapterError(
                "open311_validation_failed", "service_code and description are required"
            )
        request_id = f"SYN311-{uuid4().hex[:12].upper()}"
        record = {
            "service_request_id": request_id,
            "service_code": service_code,
            "description": description,
            "status": "open",
            "requested_datetime": datetime.now(timezone.utc).isoformat(),
            "updated_datetime": datetime.now(timezone.utc).isoformat(),
            "address_string": payload.get("address_string"),
            "lat": payload.get("lat"),
            "long": payload.get("long"),
        }
        self.requests[request_id] = record
        result = AdapterResult(command_id, True, request_id, "open311_created")
        self.commands[command_id] = result
        return result

    def assign(self, command: AssignmentCommand) -> AdapterResult:
        return self.create_or_import(
            command.command_id,
            {
                "service_code": command.service_id,
                "description": "Assignment created by an authorized Pulse 109 operator.",
            },
        )

    def push_status(self, command_id: str, payload: dict[str, object]) -> AdapterResult:
        prior = self.commands.get(command_id)
        if prior is not None:
            return prior
        external_id = payload.get("external_id")
        if not isinstance(external_id, str) or external_id not in self.requests:
            raise PermanentAdapterError("open311_request_not_found", "Synthetic request not found")
        status = payload.get("status")
        if status not in {"open", "closed"}:
            raise PermanentAdapterError("open311_status_unknown", "Status requires mapping review")
        self.requests[external_id]["status"] = status
        self.requests[external_id]["updated_datetime"] = datetime.now(timezone.utc).isoformat()
        result = AdapterResult(command_id, True, external_id, "open311_status_updated")
        self.commands[command_id] = result
        return result

    def fetch_status(self, request_id: str, cursor: str | None = None) -> list[RemoteStatusEvent]:
        del cursor
        record = self.requests.get(request_id)
        if record is None:
            return []
        now = datetime.now(timezone.utc)
        return [
            RemoteStatusEvent(
                source_event_id=f"{request_id}:{record['updated_datetime']}",
                request_id=request_id,
                source_system=self.adapter_id,
                source_status=str(record["status"]),
                occurred_at=None,
                observed_at=now,
                payload={"synthetic_only": True},
            )
        ]

    def fetch_catalog(self) -> list[dict[str, object]]:
        return [
            {
                "service_code": "service:roads",
                "service_name": "Synthetic roads service",
                "description": "Contract fixture only",
                "metadata": False,
                "type": "realtime",
                "keywords": "synthetic",
                "group": "Pulse 109 demo",
            }
        ]

    def attach_evidence(self, command_id: str, payload: dict[str, object]) -> AdapterResult:
        del payload
        result = AdapterResult(command_id, True, f"SYN-EVIDENCE-{command_id}", "stored")
        self.commands[command_id] = result
        return result

    def map_status(self, source_status: str) -> StatusMapping:
        mapping = {"open": "in_progress", "closed": "resolved"}
        canonical = cast(LifecycleStatus | None, mapping.get(source_status))
        return StatusMapping(
            source_system=self.adapter_id,
            mapping_version="open311-v2-synthetic-1.0.0",
            source_status=source_status,
            canonical_status=canonical,
            review_required=canonical is None,
        )
