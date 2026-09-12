"""Create incident membership and adapter delivery state."""

from alembic import op

revision = "0006_m5_incidents_integration"
down_revision = "0005_m4_retrieval_duplicates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE incidents.incident (
            incident_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            state varchar(24) NOT NULL DEFAULT 'proposed'
                CHECK (state IN ('proposed', 'confirmed', 'rejected', 'monitoring', 'resolved', 'closed')),
            region_id varchar(32) NOT NULL,
            topic_id varchar(128) NOT NULL,
            service_id varchar(128),
            proposal_source varchar(24) NOT NULL CHECK (proposal_source IN ('operator', 'rule', 'model')),
            geo_id varchar(128),
            window_started_at timestamptz,
            window_ended_at timestamptz,
            rationale jsonb NOT NULL DEFAULT '[]'::jsonb,
            version bigint NOT NULL DEFAULT 1 CHECK (version > 0),
            idempotency_key varchar(128) NOT NULL,
            correlation_id varchar(128) NOT NULL,
            created_by_token varchar(256) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (region_id, idempotency_key),
            CHECK (window_ended_at IS NULL OR window_started_at IS NULL OR window_ended_at >= window_started_at)
        );

        CREATE TABLE incidents.membership_decision (
            membership_decision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            incident_id uuid NOT NULL REFERENCES incidents.incident(incident_id),
            request_id uuid NOT NULL REFERENCES appeals.appeal(request_id),
            incident_version bigint NOT NULL CHECK (incident_version > 0),
            decision varchar(16) NOT NULL CHECK (decision IN ('confirm', 'reject', 'remove')),
            reason_code varchar(128) NOT NULL,
            note text,
            evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
            actor_token varchar(256) NOT NULL,
            idempotency_key varchar(128) NOT NULL,
            correlation_id varchar(128) NOT NULL,
            decided_at timestamptz NOT NULL,
            UNIQUE (incident_id, idempotency_key)
        );
        CREATE INDEX membership_decision_current_idx ON incidents.membership_decision
            (incident_id, request_id, decided_at DESC);

        CREATE TABLE integration.status_mapping (
            source_system_id uuid NOT NULL REFERENCES integration.source_system(id),
            mapping_version varchar(64) NOT NULL,
            source_status varchar(128) NOT NULL,
            canonical_status varchar(32)
                CHECK (canonical_status IS NULL OR canonical_status IN
                    ('new', 'triage', 'assigned', 'accepted', 'in_progress', 'waiting', 'resolved', 'closed', 'reopened', 'cancelled')),
            review_state varchar(24) NOT NULL DEFAULT 'approved'
                CHECK (review_state IN ('approved', 'mapping_review', 'retired')),
            effective_from timestamptz NOT NULL,
            effective_to timestamptz,
            synthetic_only boolean NOT NULL DEFAULT true,
            PRIMARY KEY (source_system_id, mapping_version, source_status),
            CHECK ((review_state = 'approved') = (canonical_status IS NOT NULL)),
            CHECK (effective_to IS NULL OR effective_to > effective_from)
        );

        CREATE TABLE integration.delivery_attempt (
            attempt_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            outbox_event_id uuid NOT NULL REFERENCES integration.outbox(event_id),
            adapter_id varchar(128) NOT NULL,
            attempt_number integer NOT NULL CHECK (attempt_number > 0),
            state varchar(24) NOT NULL CHECK (state IN ('confirmed', 'retrying', 'failed_permanent')),
            error_code varchar(128),
            external_id varchar(256),
            response_hash char(64) CHECK (response_hash IS NULL OR response_hash ~ '^[0-9a-f]{64}$'),
            attempted_at timestamptz NOT NULL,
            next_attempt_at timestamptz,
            latency_ms integer NOT NULL CHECK (latency_ms >= 0),
            UNIQUE (outbox_event_id, attempt_number),
            CHECK (state <> 'confirmed' OR external_id IS NOT NULL),
            CHECK (state <> 'retrying' OR next_attempt_at IS NOT NULL)
        );

        CREATE TABLE integration.dead_letter (
            dead_letter_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            outbox_event_id uuid NOT NULL UNIQUE REFERENCES integration.outbox(event_id),
            adapter_id varchar(128) NOT NULL,
            error_code varchar(128) NOT NULL,
            payload_hash char(64) NOT NULL CHECK (payload_hash ~ '^[0-9a-f]{64}$'),
            attempts integer NOT NULL CHECK (attempts > 0),
            review_state varchar(24) NOT NULL DEFAULT 'unreviewed'
                CHECK (review_state IN ('unreviewed', 'requeue_approved', 'resolved', 'dismissed')),
            created_at timestamptz NOT NULL,
            reviewed_at timestamptz,
            reviewed_by_token varchar(256),
            review_reason text
        );

        CREATE TABLE integration.checkpoint (
            adapter_id varchar(128) NOT NULL,
            partition_key varchar(128) NOT NULL,
            cursor_value varchar(512) NOT NULL,
            last_successful_at timestamptz NOT NULL,
            lag_seconds integer NOT NULL CHECK (lag_seconds >= 0),
            reconciliation_hash char(64) NOT NULL CHECK (reconciliation_hash ~ '^[0-9a-f]{64}$'),
            updated_at timestamptz NOT NULL,
            PRIMARY KEY (adapter_id, partition_key)
        );

        CREATE TABLE integration.source_event_receipt (
            source_system_id uuid NOT NULL REFERENCES integration.source_system(id),
            source_event_id varchar(128) NOT NULL,
            source_status varchar(128) NOT NULL,
            mapping_version varchar(64) NOT NULL,
            payload_hash char(64) NOT NULL CHECK (payload_hash ~ '^[0-9a-f]{64}$'),
            observed_at timestamptz NOT NULL,
            applied_event_id uuid REFERENCES appeals.appeal_event(event_id),
            review_state varchar(24) NOT NULL CHECK (review_state IN ('applied', 'mapping_review')),
            PRIMARY KEY (source_system_id, source_event_id)
        );

        CREATE TRIGGER membership_decision_append_only
            BEFORE UPDATE OR DELETE ON incidents.membership_decision
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER delivery_attempt_append_only
            BEFORE UPDATE OR DELETE ON integration.delivery_attempt
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        CREATE TRIGGER source_event_receipt_append_only
            BEFORE UPDATE OR DELETE ON integration.source_event_receipt
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
        """
    )


def downgrade() -> None:
    for table, trigger in (
        ("integration.source_event_receipt", "source_event_receipt_append_only"),
        ("integration.delivery_attempt", "delivery_attempt_append_only"),
        ("incidents.membership_decision", "membership_decision_append_only"),
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
    for table in (
        "integration.source_event_receipt",
        "integration.checkpoint",
        "integration.dead_letter",
        "integration.delivery_attempt",
        "integration.status_mapping",
        "incidents.membership_decision",
        "incidents.incident",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")
