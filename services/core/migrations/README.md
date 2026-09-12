# Core database migrations

Run Alembic from `services/core` with `DATABASE_URL` set. The URL may use a
SQLAlchemy synchronous or asynchronous PostgreSQL driver. Migrations are
forward-only and must not be edited after they have been applied.
