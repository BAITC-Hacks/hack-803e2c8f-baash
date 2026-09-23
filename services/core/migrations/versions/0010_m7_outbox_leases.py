"""Add durable outbox worker lease and external receipt fields."""

from alembic import op

revision = "0010_m7_outbox_leases"
down_revision = "0009_m7_versioned_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE integration.outbox
            ADD COLUMN processing_started_at timestamptz,
            ADD COLUMN worker_id varchar(128),
            ADD COLUMN external_id varchar(256);
        CREATE INDEX outbox_processing_lease_idx
            ON integration.outbox (processing_started_at)
            WHERE status = 'processing';
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS integration.outbox_processing_lease_idx")
    op.execute(
        """
        ALTER TABLE integration.outbox
            DROP COLUMN IF EXISTS external_id,
            DROP COLUMN IF EXISTS worker_id,
            DROP COLUMN IF EXISTS processing_started_at;
        """
    )
