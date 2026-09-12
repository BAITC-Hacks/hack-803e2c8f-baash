import os

import psycopg
import pytest


@pytest.mark.integration
def test_required_database_extensions_and_migration_head() -> None:
    database_url = os.getenv("PULSE109_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PULSE109_TEST_DATABASE_URL is not configured")

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT extname FROM pg_extension "
            "WHERE extname IN ('postgis', 'vector') ORDER BY extname"
        )
        assert [row[0] for row in cursor.fetchall()] == ["postgis", "vector"]
        cursor.execute("SELECT version_num FROM alembic_version")
        assert cursor.fetchone() is not None
