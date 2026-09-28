from __future__ import annotations

import ipaddress
import re
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PULSE109_",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Literal["local", "development", "test", "pilot", "production"] = "local"
    profile: Literal["local", "demo", "pilot", "production"] | None = None
    database_url: str = "postgresql+psycopg://pulse109:pulse109-local@localhost:5432/pulse109"
    readiness_database_required: bool = True
    log_level: str = "INFO"
    service_name: str = "core-api"
    api_version: str = "1.0.0"
    max_import_rows: int = Field(default=100_000, ge=1, le=1_000_000)
    local_identity_enabled: bool = True
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_algorithms: list[str] = Field(default_factory=lambda: ["RS256"])
    otel_enabled: bool = True
    otel_exporter_endpoint: str | None = None
    otel_sample_ratio: float = Field(default=0.1, ge=0, le=1)
    manual_repository_mode: Literal["memory", "postgres"] = "memory"
    approved_legal_basis: str | None = None
    approved_retention_class: str | None = None
    replay_snapshot_dir: str = ".data/snapshots"
    demo_attachment_dir: str = ".data/attachments"
    control_plane_trusted_keys: list[str] = Field(default_factory=list)
    ask_inference_url: str | None = None
    ask_inference_timeout_seconds: float = Field(default=6.0, gt=0, le=30)
    ask_context_secret: str | None = Field(default=None, min_length=32, repr=False)

    @field_validator("ask_inference_url")
    @classmethod
    def private_intent_gateway(cls, value: str | None) -> str | None:
        if value is None:
            return None
        endpoint = urlsplit(value)
        if (
            endpoint.scheme not in {"http", "https"}
            or not endpoint.hostname
            or endpoint.username
            or endpoint.password
            or endpoint.path not in {"", "/"}
            or endpoint.query
            or endpoint.fragment
        ):
            raise ValueError("Ask inference requires a private HTTP base URL without credentials")
        try:
            address = ipaddress.ip_address(endpoint.hostname)
        except ValueError:
            if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", endpoint.hostname):
                raise ValueError("Ask inference requires a private service name") from None
        else:
            networks = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7")
            if not address.is_loopback and not any(
                address in ipaddress.ip_network(network) for network in networks
            ):
                raise ValueError("Ask inference requires loopback or a private network")
        _ = endpoint.port
        return value.rstrip("/")

    # Object storage. Credentials are never settings: boto3 reads them from the
    # environment or an instance role on the host, so nothing secret can reach a
    # configuration file that might be committed.
    object_storage_mode: Literal["local", "s3"] = "local"
    object_storage_bucket: str | None = None
    object_storage_prefix: str = "pulse109/artifacts"
    object_storage_endpoint: str | None = None
    object_storage_region: str | None = None

    @property
    def effective_profile(self) -> str:
        return self.profile or self.environment

    @model_validator(mode="after")
    def validate_profile_boundary(self) -> Settings:
        if self.environment in {"pilot", "production"} and self.profile not in {
            None,
            self.environment,
        }:
            raise ValueError("An operational environment cannot activate a demo or local profile")
        if self.profile in {"pilot", "production"} and self.environment != self.profile:
            raise ValueError("An operational profile requires the matching environment")
        if self.effective_profile == "demo" and not self.readiness_database_required:
            raise ValueError("The demo profile requires PostgreSQL readiness")
        if self.object_storage_mode == "s3" and not self.object_storage_bucket:
            raise ValueError("S3 object storage requires a bucket name")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
