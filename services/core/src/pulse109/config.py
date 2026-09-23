from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PULSE109_",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Literal["local", "development", "test", "pilot", "production"] = "local"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
