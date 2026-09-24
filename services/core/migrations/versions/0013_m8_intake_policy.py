"""Add immutable, approved and effective adaptive-intake policy versions."""

from alembic import op

revision = "0013_m8_intake_policy"
down_revision = "0012_m8_ownership_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS intake;
        CREATE TABLE intake.policy_version (
            region_id varchar(32) NOT NULL,
            service_id varchar(128) NOT NULL,
            service_version varchar(64) NOT NULL,
            topic_id varchar(128) NOT NULL,
            topic_version varchar(64) NOT NULL,
            version varchar(64) NOT NULL,
            state varchar(24) NOT NULL CHECK (state IN ('draft', 'approved', 'retired')),
            effective_from timestamptz NOT NULL,
            effective_to timestamptz,
            required_fields jsonb NOT NULL,
            source_ref varchar(512) NOT NULL,
            created_by_token varchar(256) NOT NULL,
            reviewed_by_token varchar(256),
            approval_ref varchar(512),
            synthetic_only boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (region_id, service_id, topic_id, version),
            FOREIGN KEY (service_id, region_id, service_version)
                REFERENCES catalog.service_version(service_id, region_id, version),
            FOREIGN KEY (topic_id, topic_version)
                REFERENCES catalog.topic_version(topic_id, version),
            CHECK (jsonb_typeof(required_fields) = 'array'),
            CHECK (effective_to IS NULL OR effective_to > effective_from),
            CHECK (state <> 'approved' OR
                   (reviewed_by_token IS NOT NULL AND approval_ref IS NOT NULL))
        );
        CREATE INDEX intake_policy_effective_idx
            ON intake.policy_version
            (region_id, service_id, topic_id, state, effective_from, effective_to)
            WHERE state = 'approved';
        CREATE TRIGGER intake_policy_version_append_only
            BEFORE UPDATE OR DELETE ON intake.policy_version
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS intake CASCADE")
