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


@lru_cache
def get_settings() -> Settings:
    return Settings()
