"""Add immutable, effective regional unit-to-organization mappings."""

from alembic import op

revision = "0018_m8_unit_organization_crosswalk"
down_revision = "0017_m11_replay_lab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE ownership.unit_organization_mapping (
            mapping_id uuid PRIMARY KEY,
            region_id varchar(32) NOT NULL CHECK (region_id ~ '^[A-Z0-9_-]{2,32}$'),
            service_id varchar(128) NOT NULL,
            unit_id varchar(128) NOT NULL,
            organization_id varchar(128) NOT NULL,
            organization_version varchar(64) NOT NULL,
            version varchar(64) NOT NULL,
            effective_from timestamptz NOT NULL,
            effective_to timestamptz,
            state varchar(24) NOT NULL CHECK (state IN ('draft', 'approved', 'retired')),
            source_ref varchar(71) NOT NULL CHECK (source_ref ~ '^sha256:[0-9a-f]{64}$'),
            created_by_token varchar(256) NOT NULL,
            reviewed_by_token varchar(256),
            approval_ref varchar(71) CHECK (approval_ref ~ '^sha256:[0-9a-f]{64}$'),
            synthetic_only boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (region_id, organization_id, organization_version)
                REFERENCES ownership.organization_version(region_id, organization_id, version),
            UNIQUE (region_id, service_id, unit_id, version),
            CHECK (length(btrim(service_id)) > 0 AND length(btrim(unit_id)) > 0),
            CHECK (effective_to IS NULL OR effective_to > effective_from),
            CHECK (state <> 'approved' OR
                   (reviewed_by_token IS NOT NULL AND approval_ref IS NOT NULL
                    AND reviewed_by_token <> created_by_token))
        );
        ALTER TABLE ownership.unit_organization_mapping
            ADD CONSTRAINT unit_organization_no_approved_overlap
            EXCLUDE USING gist (
                region_id WITH =,
                service_id WITH =,
                unit_id WITH =,
                tstzrange(effective_from, effective_to, '[)') WITH &&
            ) WHERE (state = 'approved');
        CREATE INDEX unit_organization_lookup_idx
            ON ownership.unit_organization_mapping
            (region_id, service_id, unit_id, effective_from DESC)
            WHERE state = 'approved';
        ALTER TABLE ownership.handoff_outcome
            ADD COLUMN mapping_id uuid REFERENCES ownership.unit_organization_mapping(mapping_id);
        CREATE TRIGGER unit_organization_append_only
            BEFORE UPDATE OR DELETE ON ownership.unit_organization_mapping
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE ownership.handoff_outcome DROP COLUMN IF EXISTS mapping_id")
    op.execute("DROP TABLE IF EXISTS ownership.unit_organization_mapping")
