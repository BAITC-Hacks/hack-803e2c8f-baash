from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
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
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
