"""Add governed effective-dated routing, SLA, and confidence policies."""

from alembic import op

revision = "0009_m7_versioned_policies"
down_revision = "0008_m7_manual_path_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE catalog.policy_version (
            policy_type varchar(24) NOT NULL
                CHECK (policy_type IN ('routing', 'sla', 'confidence')),
            region_id varchar(32) NOT NULL,
            version varchar(64) NOT NULL,
            state varchar(24) NOT NULL
                CHECK (state IN ('draft', 'pending_approval', 'approved', 'retired')),
            effective_from timestamptz,
            effective_to timestamptz,
            parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_by_token varchar(256) NOT NULL,
            reviewed_by_token varchar(256),
            approval_ref varchar(512),
            rollback_version varchar(64),
            synthetic_only boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (policy_type, region_id, version),
            CHECK ((state = 'approved') =
                   (effective_from IS NOT NULL AND reviewed_by_token IS NOT NULL
                    AND approval_ref IS NOT NULL)),
            CHECK (effective_to IS NULL OR effective_from IS NULL
                   OR effective_to > effective_from),
            CHECK (rollback_version IS NULL OR rollback_version <> version)
        );
        CREATE INDEX policy_version_effective_idx
            ON catalog.policy_version (region_id, policy_type, state, effective_from, effective_to);

        CREATE TABLE catalog.policy_review (
            review_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_type varchar(24) NOT NULL,
            region_id varchar(32) NOT NULL,
            version varchar(64) NOT NULL,
            decision varchar(24) NOT NULL
                CHECK (decision IN ('approve', 'reject', 'retire', 'rollback')),
            reason_code varchar(128) NOT NULL,
            actor_token varchar(256) NOT NULL,
            correlation_id varchar(128) NOT NULL,
            decided_at timestamptz NOT NULL,
            FOREIGN KEY (policy_type, region_id, version)
                REFERENCES catalog.policy_version(policy_type, region_id, version)
        );
        CREATE TRIGGER policy_review_append_only
            BEFORE UPDATE OR DELETE ON catalog.policy_review
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS policy_review_append_only ON catalog.policy_review")
    op.execute("DROP TABLE IF EXISTS catalog.policy_review")
    op.execute("DROP TABLE IF EXISTS catalog.policy_version")
