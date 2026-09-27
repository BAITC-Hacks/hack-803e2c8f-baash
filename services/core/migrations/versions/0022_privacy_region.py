"""Bind private references to a verified region; leave legacy unknowns inaccessible."""

from alembic import op

revision = "0022_privacy_region"
down_revision = "0021_incident_topology"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE privacy.private_ref ADD COLUMN region_id varchar(32)")
    op.execute(
        "ALTER TABLE privacy.private_ref ADD CONSTRAINT private_ref_region_check "
        "CHECK (region_id ~ '^[A-Z0-9_-]{2,32}$')"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE privacy.private_ref DROP COLUMN region_id")
