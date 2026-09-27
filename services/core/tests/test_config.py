import pytest
from pulse109.config import Settings


def test_local_defaults_keep_external_integrations_optional() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "local"
    assert settings.service_name == "core-api"
    assert settings.max_import_rows == 100_000


def test_demo_profile_forces_postgres_readiness_and_rejects_operational_mismatch() -> None:
    assert Settings(_env_file=None, profile="demo").effective_profile == "demo"
    with pytest.raises(ValueError, match="PostgreSQL readiness"):
        Settings(_env_file=None, profile="demo", readiness_database_required=False)
    with pytest.raises(ValueError, match="operational environment"):
        Settings(_env_file=None, environment="production", profile="demo")
