from scripts.run_integration_tests import isolated_urls


def test_isolated_urls_keep_server_and_replace_only_database() -> None:
    admin_url, test_url = isolated_urls(
        "postgresql+psycopg://operator:secret@db.example:5433/original?sslmode=require",
        "pulse109_integration_abc",
    )
    assert (
        admin_url == "postgresql+psycopg://operator:secret@db.example:5433/postgres?sslmode=require"
    )
    assert test_url == (
        "postgresql+psycopg://operator:secret@db.example:5433/pulse109_integration_abc?sslmode=require"
    )
