"""Complete the durable manual-path projection used by the core API."""

from alembic import op

revision = "0008_m7_manual_path_persistence"
down_revision = "0007_m6_analytics_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE appeals.appeal
            ADD COLUMN received_at timestamptz,
            ADD COLUMN received_at_quality varchar(32) NOT NULL DEFAULT 'missing'
                CHECK (received_at_quality IN ('exact', 'source_tz_assumed', 'date_only', 'missing')),
            ADD COLUMN media_refs jsonb NOT NULL DEFAULT '[]'::jsonb;

        ALTER TABLE appeals.appeal
            ADD CONSTRAINT appeal_received_time_quality_check CHECK (
                (received_at_quality NOT IN ('missing', 'date_only') OR received_at IS NULL)
                AND (received_at IS NOT NULL OR received_at_quality IN ('missing', 'date_only'))
                AND (received_at_quality <> 'source_tz_assumed' OR source_timezone IS NOT NULL)
            );

        ALTER TABLE appeals.appeal
            DROP CONSTRAINT IF EXISTS appeal_status_check;
        ALTER TABLE appeals.appeal
            ADD CONSTRAINT appeal_status_check CHECK
                (status IN ('new', 'triage', 'assigned', 'accepted', 'in_progress',
                            'waiting', 'resolved', 'closed', 'reopened', 'cancelled'));

        CREATE TABLE privacy.appeal_content (
            appeal_id uuid PRIMARY KEY REFERENCES appeals.appeal(request_id),
            redacted_text text,
            created_at timestamptz NOT NULL DEFAULT now(),
            CHECK (redacted_text IS NULL OR length(redacted_text) <= 20000)
        );

        CREATE TRIGGER appeal_content_append_only
            BEFORE UPDATE OR DELETE ON privacy.appeal_content
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS appeal_content_append_only ON privacy.appeal_content")
    op.execute("DROP TABLE IF EXISTS privacy.appeal_content")
    op.execute("ALTER TABLE appeals.appeal DROP CONSTRAINT IF EXISTS appeal_status_check")
    op.execute(
        """
        ALTER TABLE appeals.appeal
            ADD CONSTRAINT appeal_status_check CHECK
                (status IN ('new', 'triage', 'assigned', 'in_progress', 'resolved',
                            'closed', 'reopened', 'cancelled'));
        ALTER TABLE appeals.appeal
            DROP CONSTRAINT IF EXISTS appeal_received_time_quality_check;
        ALTER TABLE appeals.appeal
            DROP COLUMN IF EXISTS media_refs,
            DROP COLUMN IF EXISTS received_at_quality,
            DROP COLUMN IF EXISTS received_at;
        """
    )
