"""Add append-only, approved model-artifact-scoped confidence policies."""

from alembic import op

revision = "0014_m8_confidence_policy"
down_revision = "0013_m8_intake_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE triage.confidence_policy_version (
            policy_id uuid PRIMARY KEY,
            region_id varchar(32) NOT NULL,
            artifact_sha256 varchar(64) NOT NULL,
            taxonomy_version varchar(64) NOT NULL,
            preprocess_version varchar(64) NOT NULL,
            version varchar(64) NOT NULL,
            state varchar(24) NOT NULL CHECK (state IN ('draft', 'approved', 'retired')),
            effective_from timestamptz NOT NULL,
            effective_to timestamptz,
            high_min numeric(6,5) NOT NULL,
            medium_min numeric(6,5) NOT NULL,
            abstain_below numeric(6,5) NOT NULL,
            source_ref varchar(512) NOT NULL,
            created_by_token varchar(256) NOT NULL,
            reviewed_by_token varchar(256),
            approval_ref varchar(512),
            synthetic_only boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (region_id, artifact_sha256, taxonomy_version, preprocess_version, version),
            CHECK (region_id ~ '^[A-Z0-9_-]{2,32}$'),
            CHECK (artifact_sha256 ~ '^[a-f0-9]{64}$'),
            CHECK (taxonomy_version ~ '^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$'),
            CHECK (preprocess_version ~ '^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$'),
            CHECK (effective_to IS NULL OR effective_to > effective_from),
            CHECK (high_min BETWEEN 0 AND 1),
            CHECK (medium_min BETWEEN 0 AND 1),
            CHECK (abstain_below BETWEEN 0 AND 1),
            CHECK (high_min >= medium_min AND medium_min >= abstain_below),
            CHECK (state <> 'approved' OR
                   (reviewed_by_token IS NOT NULL AND approval_ref IS NOT NULL)),
            CHECK (length(btrim(version)) > 0),
            CHECK (length(btrim(source_ref)) > 0),
            CHECK (length(btrim(created_by_token)) > 0)
        );
        CREATE INDEX confidence_policy_effective_idx
            ON triage.confidence_policy_version
            (region_id, artifact_sha256, taxonomy_version, preprocess_version,
             state, effective_from, effective_to)
            WHERE state = 'approved';
        CREATE TRIGGER confidence_policy_append_only
            BEFORE UPDATE OR DELETE ON triage.confidence_policy_version
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS triage.confidence_policy_version")
