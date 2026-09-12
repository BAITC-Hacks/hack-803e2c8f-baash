"""Create the manual routing path and versioned synthetic catalog."""

from alembic import op

revision = "0003_m2_manual_path"
down_revision = "0002_m1_data_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE catalog.topic_version (
            topic_id varchar(128) NOT NULL,
            version varchar(64) NOT NULL,
            effective_from timestamptz NOT NULL,
            effective_to timestamptz,
            display_name jsonb NOT NULL,
            active boolean NOT NULL DEFAULT true,
            synthetic_only boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (topic_id, version),
            CHECK (effective_to IS NULL OR effective_to > effective_from)
        );

        CREATE TABLE catalog.service_version (
            service_id varchar(128) NOT NULL,
            region_id varchar(32) NOT NULL,
            version varchar(64) NOT NULL,
            effective_from timestamptz NOT NULL,
            effective_to timestamptz,
            display_name jsonb NOT NULL,
            required_fields jsonb NOT NULL DEFAULT '[]'::jsonb,
            active boolean NOT NULL DEFAULT true,
            synthetic_only boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (service_id, region_id, version),
            CHECK (effective_to IS NULL OR effective_to > effective_from)
        );
        CREATE INDEX service_version_effective_idx ON catalog.service_version
            (region_id, effective_from DESC, service_id);

        CREATE TABLE catalog.service_topic (
            service_id varchar(128) NOT NULL,
            region_id varchar(32) NOT NULL,
            service_version varchar(64) NOT NULL,
            topic_id varchar(128) NOT NULL,
            topic_version varchar(64) NOT NULL,
            PRIMARY KEY (service_id, region_id, service_version, topic_id, topic_version),
            FOREIGN KEY (service_id, region_id, service_version)
                REFERENCES catalog.service_version(service_id, region_id, version),
            FOREIGN KEY (topic_id, topic_version)
                REFERENCES catalog.topic_version(topic_id, version)
        );

        CREATE TABLE triage.operator_decision (
            decision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id uuid NOT NULL REFERENCES appeals.appeal(request_id),
            request_version bigint NOT NULL CHECK (request_version > 0),
            new_version bigint NOT NULL CHECK (new_version = request_version + 1),
            recommendation_id uuid,
            topic_id varchar(128) NOT NULL,
            service_id varchar(128) NOT NULL,
            priority varchar(32) NOT NULL
                CHECK (priority IN ('routine', 'elevated', 'urgent', 'emergency_handoff')),
            action varchar(32) NOT NULL CHECK (action IN ('accepted', 'corrected', 'manual')),
            correction_reason text,
            operator_note text,
            operator_token varchar(256) NOT NULL,
            region_id varchar(32) NOT NULL,
            idempotency_key varchar(128) NOT NULL,
            correlation_id varchar(128) NOT NULL,
            decided_at timestamptz NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            CHECK (action <> 'corrected' OR (correction_reason IS NOT NULL AND length(trim(correction_reason)) > 0)),
            CHECK (action = 'manual' OR recommendation_id IS NOT NULL),
            UNIQUE (request_id, new_version),
            UNIQUE (region_id, idempotency_key)
        );
        CREATE INDEX operator_decision_request_idx ON triage.operator_decision
            (request_id, decided_at DESC);

        CREATE TABLE appeals.assignment (
            assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id uuid NOT NULL REFERENCES appeals.appeal(request_id),
            request_version bigint NOT NULL CHECK (request_version > 0),
            new_version bigint NOT NULL CHECK (new_version = request_version + 1),
            from_service_id varchar(128),
            to_service_id varchar(128) NOT NULL,
            assignee_unit_id varchar(128),
            reason_code varchar(128) NOT NULL,
            expected_due_at timestamptz,
            policy_version varchar(64),
            actor_token varchar(256) NOT NULL,
            region_id varchar(32) NOT NULL,
            idempotency_key varchar(128) NOT NULL,
            correlation_id varchar(128) NOT NULL,
            outbox_event_id uuid NOT NULL REFERENCES integration.outbox(event_id),
            assigned_at timestamptz NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (request_id, new_version),
            UNIQUE (region_id, idempotency_key)
        );
        CREATE INDEX assignment_request_idx ON appeals.assignment (request_id, assigned_at DESC);

        CREATE TRIGGER operator_decision_append_only
            BEFORE UPDATE OR DELETE ON triage.operator_decision
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER assignment_append_only
            BEFORE UPDATE OR DELETE ON appeals.assignment
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS assignment_append_only ON appeals.assignment")
    op.execute("DROP TRIGGER IF EXISTS operator_decision_append_only ON triage.operator_decision")
    for table in (
        "appeals.assignment",
        "triage.operator_decision",
        "catalog.service_topic",
        "catalog.service_version",
        "catalog.topic_version",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
