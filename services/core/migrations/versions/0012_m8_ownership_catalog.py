"""Add immutable regional ownership facts and effective responsibility rules."""

from alembic import op

revision = "0012_m8_ownership_catalog"
down_revision = "0011_m7_incident_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS ownership;

        CREATE TABLE ownership.organization_version (
            region_id varchar(32) NOT NULL,
            organization_id varchar(128) NOT NULL,
            version varchar(64) NOT NULL,
            display_name jsonb NOT NULL,
            organization_type varchar(64) NOT NULL,
            effective_from timestamptz NOT NULL,
            effective_to timestamptz,
            state varchar(24) NOT NULL CHECK (state IN ('draft', 'approved', 'retired')),
            source_ref varchar(512) NOT NULL,
            created_by_token varchar(256) NOT NULL,
            reviewed_by_token varchar(256),
            approval_ref varchar(512),
            synthetic_only boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (region_id, organization_id, version),
            CHECK (jsonb_typeof(display_name) = 'object'),
            CHECK (effective_to IS NULL OR effective_to > effective_from),
            CHECK (state <> 'approved' OR
                   (reviewed_by_token IS NOT NULL AND approval_ref IS NOT NULL))
        );

        CREATE TABLE ownership.jurisdiction_version (
            region_id varchar(32) NOT NULL,
            jurisdiction_id varchar(128) NOT NULL,
            version varchar(64) NOT NULL,
            display_name jsonb NOT NULL,
            boundary geometry(MultiPolygon, 4326),
            effective_from timestamptz NOT NULL,
            effective_to timestamptz,
            state varchar(24) NOT NULL CHECK (state IN ('draft', 'approved', 'retired')),
            source_ref varchar(512) NOT NULL,
            created_by_token varchar(256) NOT NULL,
            reviewed_by_token varchar(256),
            approval_ref varchar(512),
            synthetic_only boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (region_id, jurisdiction_id, version),
            CHECK (jsonb_typeof(display_name) = 'object'),
            CHECK (boundary IS NULL OR ST_IsValid(boundary)),
            CHECK (effective_to IS NULL OR effective_to > effective_from),
            CHECK (state <> 'approved' OR
                   (reviewed_by_token IS NOT NULL AND approval_ref IS NOT NULL))
        );
        CREATE INDEX jurisdiction_boundary_gist_idx
            ON ownership.jurisdiction_version USING GIST (boundary)
            WHERE state = 'approved';

        CREATE TABLE ownership.asset_version (
            region_id varchar(32) NOT NULL,
            asset_id varchar(128) NOT NULL,
            version varchar(64) NOT NULL,
            asset_class varchar(128) NOT NULL,
            jurisdiction_id varchar(128),
            jurisdiction_version varchar(64),
            owner_organization_id varchar(128),
            owner_organization_version varchar(64),
            operator_organization_id varchar(128),
            operator_organization_version varchar(64),
            location geography(Point, 4326),
            effective_from timestamptz NOT NULL,
            effective_to timestamptz,
            state varchar(24) NOT NULL CHECK (state IN ('draft', 'approved', 'retired')),
            source_ref varchar(512) NOT NULL,
            created_by_token varchar(256) NOT NULL,
            reviewed_by_token varchar(256),
            approval_ref varchar(512),
            synthetic_only boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (region_id, asset_id, version),
            FOREIGN KEY (region_id, jurisdiction_id, jurisdiction_version)
                REFERENCES ownership.jurisdiction_version(region_id, jurisdiction_id, version),
            FOREIGN KEY (region_id, owner_organization_id, owner_organization_version)
                REFERENCES ownership.organization_version(region_id, organization_id, version),
            FOREIGN KEY (region_id, operator_organization_id, operator_organization_version)
                REFERENCES ownership.organization_version(region_id, organization_id, version),
            CHECK ((jurisdiction_id IS NULL) = (jurisdiction_version IS NULL)),
            CHECK ((owner_organization_id IS NULL) = (owner_organization_version IS NULL)),
            CHECK ((operator_organization_id IS NULL) = (operator_organization_version IS NULL)),
            CHECK (effective_to IS NULL OR effective_to > effective_from),
            CHECK (state <> 'approved' OR
                   (reviewed_by_token IS NOT NULL AND approval_ref IS NOT NULL))
        );
        CREATE INDEX asset_location_gist_idx
            ON ownership.asset_version USING GIST (location)
            WHERE state = 'approved';

        CREATE TABLE ownership.responsibility_rule_version (
            region_id varchar(32) NOT NULL,
            rule_id varchar(128) NOT NULL,
            version varchar(64) NOT NULL,
            service_id varchar(128) NOT NULL,
            service_version varchar(64) NOT NULL,
            organization_id varchar(128) NOT NULL,
            organization_version varchar(64) NOT NULL,
            jurisdiction_id varchar(128),
            jurisdiction_version varchar(64),
            asset_id varchar(128),
            asset_version varchar(64),
            effective_from timestamptz NOT NULL,
            effective_to timestamptz,
            state varchar(24) NOT NULL CHECK (state IN ('draft', 'approved', 'retired')),
            reason_code varchar(128) NOT NULL,
            source_ref varchar(512) NOT NULL,
            created_by_token varchar(256) NOT NULL,
            reviewed_by_token varchar(256),
            approval_ref varchar(512),
            synthetic_only boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (region_id, rule_id, version),
            FOREIGN KEY (service_id, region_id, service_version)
                REFERENCES catalog.service_version(service_id, region_id, version),
            FOREIGN KEY (region_id, organization_id, organization_version)
                REFERENCES ownership.organization_version(region_id, organization_id, version),
            FOREIGN KEY (region_id, jurisdiction_id, jurisdiction_version)
                REFERENCES ownership.jurisdiction_version(region_id, jurisdiction_id, version),
            FOREIGN KEY (region_id, asset_id, asset_version)
                REFERENCES ownership.asset_version(region_id, asset_id, version),
            CHECK ((jurisdiction_id IS NULL) = (jurisdiction_version IS NULL)),
            CHECK ((asset_id IS NULL) = (asset_version IS NULL)),
            CHECK (effective_to IS NULL OR effective_to > effective_from),
            CHECK (state <> 'approved' OR
                   (reviewed_by_token IS NOT NULL AND approval_ref IS NOT NULL))
        );
        CREATE INDEX responsibility_rule_match_idx
            ON ownership.responsibility_rule_version
            (region_id, service_id, state, effective_from, effective_to)
            WHERE state = 'approved';
        CREATE INDEX responsibility_rule_asset_idx
            ON ownership.responsibility_rule_version (region_id, asset_id)
            WHERE state = 'approved' AND asset_id IS NOT NULL;

        ALTER TABLE appeals.assignment
            ADD CONSTRAINT assignment_identity_region_unique
            UNIQUE (assignment_id, request_id, region_id);

        CREATE TABLE ownership.handoff_outcome (
            outcome_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            region_id varchar(32) NOT NULL,
            request_id uuid NOT NULL REFERENCES appeals.appeal(request_id),
            assignment_id uuid NOT NULL,
            organization_id varchar(128) NOT NULL,
            disposition varchar(24) NOT NULL CHECK (disposition IN ('accepted', 'rejected')),
            reason_code varchar(128) NOT NULL,
            source_event_id varchar(256) NOT NULL,
            evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
            observed_at timestamptz NOT NULL DEFAULT now(),
            recorded_by_token varchar(256) NOT NULL,
            correlation_id varchar(128) NOT NULL,
            FOREIGN KEY (assignment_id, request_id, region_id)
                REFERENCES appeals.assignment(assignment_id, request_id, region_id),
            UNIQUE (region_id, source_event_id),
            CHECK (jsonb_typeof(evidence_refs) = 'array')
        );
        CREATE INDEX handoff_outcome_request_idx
            ON ownership.handoff_outcome (region_id, request_id, observed_at DESC);

        CREATE TRIGGER organization_version_append_only
            BEFORE UPDATE OR DELETE ON ownership.organization_version
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER jurisdiction_version_append_only
            BEFORE UPDATE OR DELETE ON ownership.jurisdiction_version
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER asset_version_append_only
            BEFORE UPDATE OR DELETE ON ownership.asset_version
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER responsibility_rule_version_append_only
            BEFORE UPDATE OR DELETE ON ownership.responsibility_rule_version
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER handoff_outcome_append_only
            BEFORE UPDATE OR DELETE ON ownership.handoff_outcome
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS ownership CASCADE")
    op.execute("ALTER TABLE appeals.assignment DROP CONSTRAINT assignment_identity_region_unique")
