"""Add supervised incident merge, split and reopen provenance."""

from alembic import op

revision = "0021_incident_topology"
down_revision = "0020_bundle_activation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE incidents.incident DROP CONSTRAINT incident_state_check;
        ALTER TABLE incidents.incident ADD CONSTRAINT incidents_incident_state_check
            CHECK (state IN ('proposed','confirmed','rejected','monitoring','resolved','closed','superseded'));

        CREATE TABLE incidents.incident_relation_decision (
            relation_decision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            operation varchar(16) NOT NULL CHECK (operation IN ('merge','split')),
            source_incident_id uuid NOT NULL REFERENCES incidents.incident(incident_id),
            target_incident_id uuid NOT NULL REFERENCES incidents.incident(incident_id),
            source_version bigint NOT NULL CHECK (source_version > 0),
            target_version bigint NOT NULL CHECK (target_version > 0),
            command jsonb NOT NULL CHECK (jsonb_typeof(command) = 'object'),
            reason_code varchar(64) NOT NULL CHECK (reason_code ~ '^[A-Z][A-Z0-9_]{0,63}$'),
            evidence_refs jsonb NOT NULL CHECK (jsonb_typeof(evidence_refs) = 'array'),
            member_request_ids jsonb NOT NULL CHECK (jsonb_typeof(member_request_ids) = 'array'),
            actor_token varchar(256) NOT NULL,
            idempotency_key varchar(128) NOT NULL,
            correlation_id varchar(128) NOT NULL,
            decided_at timestamptz NOT NULL,
            CHECK (source_incident_id <> target_incident_id),
            UNIQUE (source_incident_id, idempotency_key)
        );
        CREATE INDEX incident_relation_source_idx
            ON incidents.incident_relation_decision(source_incident_id, decided_at, relation_decision_id);
        CREATE INDEX incident_relation_target_idx
            ON incidents.incident_relation_decision(target_incident_id, decided_at, relation_decision_id);
        CREATE TRIGGER incident_relation_decision_append_only
            BEFORE UPDATE OR DELETE ON incidents.incident_relation_decision
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS incident_relation_decision_append_only ON incidents.incident_relation_decision;
        DROP TABLE IF EXISTS incidents.incident_relation_decision;
        ALTER TABLE incidents.incident DROP CONSTRAINT incidents_incident_state_check;
        ALTER TABLE incidents.incident ADD CONSTRAINT incidents_incident_state_check
            CHECK (state IN ('proposed','confirmed','rejected','monitoring','resolved','closed'));
        """
    )
