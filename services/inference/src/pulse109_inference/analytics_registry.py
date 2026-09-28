"""Immutable local model references and human-controlled alias changes.

No model weights, credentials, mutable Hub revisions or quality claims live here.
The registry file is re-read for each request so an atomic replacement changes
aliases without restarting either the business core or model server.
"""

from __future__ import annotations

import ipaddress
import json
import re
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

import httpx
from pydantic import Field, model_validator

from .models import StrictModel

ImmutableRevision = Annotated[str, Field(pattern=r"^[0-9a-f]{40}([0-9a-f]{24})?$")]
ArtifactHash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
BoundedName = Annotated[str, Field(min_length=1, max_length=128)]


def validate_local_endpoint(endpoint: str) -> str:
    """Accept loopback, RFC1918 addresses and single-label private service names."""
    parts = urlsplit(endpoint)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
        or parts.path not in {"", "/", "/v1", "/v1/"}
    ):
        raise ValueError("model endpoint must be a local HTTP base URL without credentials")
    host = parts.hostname
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", host):
            raise ValueError("model endpoint must use a private service name") from None
    else:
        local_networks = (
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
            ipaddress.ip_network("fc00::/7"),
        )
        if not address.is_loopback and not any(address in network for network in local_networks):
            raise ValueError("model endpoint must use loopback or a private network")
    # Force evaluation of malformed ports before httpx sees this URL.
    _ = parts.port
    return endpoint.rstrip("/").removesuffix("/v1")


class AnalyticsModelArtifact(StrictModel):
    model_id: BoundedName
    endpoint: Annotated[str, Field(min_length=1, max_length=256)]
    model_revision: ImmutableRevision
    tokenizer_revision: ImmutableRevision
    artifact_sha256: ArtifactHash
    runtime: Literal["vllm", "llama_cpp", "openai_compatible_local"]
    runtime_version: BoundedName
    quantization: BoundedName
    prompt_version: Literal["analytics-intent-prompt-v1"]
    schema_version: Literal["analytics-intent-v1"]
    status: Literal["evaluation", "approved"]
    approval_ref: Annotated[str, Field(min_length=1, max_length=256)] | None = None
    evaluation_ref: Annotated[str, Field(min_length=1, max_length=256)] | None = None
    evaluation_data: Literal["synthetic_contract", "approved_questions"] = "synthetic_contract"

    @model_validator(mode="after")
    def check_artifact(self) -> AnalyticsModelArtifact:
        validate_local_endpoint(self.endpoint)
        if self.runtime_version.casefold() in {"latest", "main", "unknown"}:
            raise ValueError("runtime version must be pinned")
        if self.status == "approved" and not self.approval_ref:
            raise ValueError("approved model requires a human approval reference")
        if self.status == "approved" and (
            not self.evaluation_ref or self.evaluation_data != "approved_questions"
        ):
            raise ValueError("synthetic contract checks cannot approve a serving model")
        return self


class AnalyticsModelRegistry(StrictModel):
    registry_version: Literal["analytics-model-registry-v1"]
    models: dict[str, AnalyticsModelArtifact] = Field(default_factory=dict)
    aliases: dict[Literal["champion", "challenger", "rollback"], str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_aliases(self) -> AnalyticsModelRegistry:
        for alias, model_key in self.aliases.items():
            if model_key not in self.models:
                raise ValueError("alias must reference an immutable registered model")
            if alias in {"champion", "rollback"} and self.models[model_key].status != "approved":
                raise ValueError("serving alias requires a human-approved model")
        return self

    @classmethod
    def load(cls, path: Path) -> AnalyticsModelRegistry:
        if path.stat().st_size > 262_144:
            raise ValueError("registry exceeds size limit")
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


async def model_is_ready(artifact: AnalyticsModelArtifact, client: httpx.AsyncClient) -> bool:
    """Verify server health and the exact served model identifier before alias change."""
    base_url = validate_local_endpoint(artifact.endpoint)
    try:
        health = await client.get(f"{base_url}/health")
        health.raise_for_status()
        response = await client.get(f"{base_url}/v1/models")
        response.raise_for_status()
        document = response.json()
        return isinstance(document, dict) and any(
            isinstance(item, dict) and item.get("id") == artifact.model_id
            for item in document.get("data", [])
        )
    except (httpx.HTTPError, ValueError, TypeError):
        return False


async def prepare_alias_change(
    registry: AnalyticsModelRegistry,
    *,
    action: Literal["promote", "rollback"],
    approval_ref: str,
    client: httpx.AsyncClient,
) -> AnalyticsModelRegistry:
    """Return a reviewable replacement; writing/publishing it is an operator action."""
    if not approval_ref.strip() or len(approval_ref) > 256:
        raise ValueError("alias change requires an explicit human approval reference")
    source_alias: Literal["challenger", "rollback"] = (
        "challenger" if action == "promote" else "rollback"
    )
    model_key = registry.aliases.get(source_alias)
    if model_key is None:
        raise ValueError("requested alias is not configured")
    artifact = registry.models[model_key]
    if not await model_is_ready(artifact, client):
        raise ValueError("candidate model server is not ready")
    document = json.loads(registry.model_dump_json())
    document["models"][model_key]["status"] = "approved"
    document["models"][model_key]["approval_ref"] = approval_ref
    previous = registry.aliases.get("champion")
    document["aliases"]["champion"] = model_key
    if previous is not None and previous != model_key:
        document["aliases"]["rollback"] = previous
    return AnalyticsModelRegistry.model_validate(document)
