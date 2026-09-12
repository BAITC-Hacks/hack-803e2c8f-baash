from pulse109.config import Settings


def test_local_defaults_keep_external_integrations_optional() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "local"
    assert settings.service_name == "core-api"
    assert settings.max_import_rows == 100_000
