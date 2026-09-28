"""Run PostgreSQL integration tests in disposable, per-run databases.

The test suite uses module-owned schemas, so ``search_path`` cannot isolate a
run.  This runner creates one UUID-named database per pass, migrates it, runs
the real tests, then terminates only connections to that exact database before
dropping it.  The demo and caller-supplied database are never reset or reused.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from uuid import uuid4

import psycopg
from sqlalchemy.engine import make_url

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def isolated_urls(base_url: str, database_name: str) -> tuple[str, str]:
    """Return admin and isolated URLs without changing credentials or host."""

    parsed = make_url(base_url)
    if parsed.get_backend_name() != "postgresql":
        raise ValueError("PULSE109_TEST_DATABASE_URL must be a PostgreSQL URL")
    return (
        parsed.set(database="postgres").render_as_string(hide_password=False),
        parsed.set(database=database_name).render_as_string(hide_password=False),
    )


def _create_database(admin_url: str, database_name: str) -> None:
    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute(f'CREATE DATABASE "{database_name}"')


def _drop_database(admin_url: str, database_name: str) -> None:
    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (database_name,),
        )
        connection.execute(f'DROP DATABASE IF EXISTS "{database_name}"')


def _run_pass(base_url: str, pass_number: int) -> None:
    database_name = f"pulse109_integration_{uuid4().hex}"
    admin_url, test_url = isolated_urls(base_url, database_name)
    _create_database(admin_url, database_name)
    environment = os.environ | {
        "DATABASE_URL": test_url,
        "PULSE109_TEST_DATABASE_URL": test_url,
    }
    try:
        subprocess.run(  # noqa: S603
            [sys.executable, "-m", "alembic", "-c", "services/core/alembic.ini", "upgrade", "head"],
            cwd=ROOT,
            env=environment,
            check=True,
        )
        subprocess.run(  # noqa: S603
            [sys.executable, "-m", "pytest", "tests/integration", "-q"],
            cwd=ROOT,
            env=environment,
            check=True,
        )
    finally:
        _drop_database(admin_url, database_name)
    print(f"integration pass {pass_number} completed in isolated database")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=2, choices=range(1, 4))
    args = parser.parse_args(argv)
    base_url = os.environ.get("PULSE109_TEST_DATABASE_URL")
    if not base_url:
        parser.error("PULSE109_TEST_DATABASE_URL must name a PostgreSQL server database")
    for pass_number in range(1, args.runs + 1):
        _run_pass(base_url, pass_number)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
