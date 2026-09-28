"""The isolated URLs must keep the server and change only what they should.

Credentials, host, port and query options belong to the caller. The database
name is ours. The driver is pinned because the two consumers want different
things: alembic goes through SQLAlchemy, which picks psycopg2 when no driver is
named and this project does not ship it, while psycopg connects directly and
wants a plain URL.
"""

import pytest

from scripts.run_integration_tests import isolated_urls


@pytest.mark.parametrize(
    "supplied",
    [
        "postgresql+psycopg://operator:secret@db.example:5433/original?sslmode=require",
        "postgresql://operator:secret@db.example:5433/original?sslmode=require",
    ],
)
def test_isolated_urls_keep_server_and_replace_only_database(supplied: str) -> None:
    admin_url, test_url = isolated_urls(supplied, "pulse109_integration_abc")

    # The admin connection is made with psycopg directly, so it carries no driver.
    assert admin_url == "postgresql://operator:secret@db.example:5433/postgres?sslmode=require"
    # The test URL is handed to alembic through SQLAlchemy, which needs the driver.
    assert test_url == (
        "postgresql+psycopg://operator:secret@db.example:5433"
        "/pulse109_integration_abc?sslmode=require"
    )


def test_a_url_that_is_not_postgresql_is_refused() -> None:
    with pytest.raises(ValueError, match="PostgreSQL"):
        isolated_urls("mysql://user:secret@host/db", "pulse109_integration_abc")
