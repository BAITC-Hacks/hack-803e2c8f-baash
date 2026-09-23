"""Persist incident proposals and append-only incident lifecycle events."""

from alembic import op

revision = "0011_m7_incident_persistence"
down_revision = "0010_m7_outbox_leases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE incidents.incident_candidate_member (
            incident_id uuid NOT NULL REFERENCES incidents.incident(incident_id),
            request_id uuid NOT NULL REFERENCES appeals.appeal(request_id),
            proposed_at timestamptz NOT NULL,
            rationale jsonb NOT NULL DEFAULT '[]'::jsonb,
            PRIMARY KEY (incident_id, request_id)
        );

        CREATE TABLE incidents.incident_event (
            event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            incident_id uuid NOT NULL REFERENCES incidents.incident(incident_id),
            event_type varchar(128) NOT NULL,
            event_version integer NOT NULL DEFAULT 1 CHECK (event_version > 0),
            incident_version bigint NOT NULL CHECK (incident_version > 0),
            region_id varchar(32) NOT NULL,
            actor_token varchar(256) NOT NULL,
            correlation_id varchar(128) NOT NULL,
            observed_at timestamptz NOT NULL,
            payload jsonb NOT NULL DEFAULT '{}'::jsonb
        );
        CREATE INDEX incident_event_timeline_idx
            ON incidents.incident_event (incident_id, observed_at, event_id);
        CREATE TRIGGER incident_event_append_only
            BEFORE UPDATE OR DELETE ON incidents.incident_event
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS incident_event_append_only ON incidents.incident_event")
    op.execute("DROP TABLE IF EXISTS incidents.incident_event")
    op.execute("DROP TABLE IF EXISTS incidents.incident_candidate_member")
