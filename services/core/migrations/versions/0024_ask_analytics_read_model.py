"""Expose PII-free analytics reads over durable operational state."""

from alembic import op

revision = "0024_ask_analytics_read_model"
down_revision = "0023_discovery_emerging_clusters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE VIEW analytics.appeal_read_model AS
        SELECT a.request_id, a.source_request_id, a.region_id, a.channel, a.language, a.status,
               a.received_at, a.received_at_quality, a.observed_at,
               d.topic_id, coalesce(assignment.to_service_id, d.service_id) AS service_id
        FROM appeals.appeal a
        LEFT JOIN LATERAL (
            SELECT topic_id, service_id FROM triage.operator_decision
            WHERE request_id = a.request_id
            ORDER BY new_version DESC LIMIT 1
        ) d ON true
        LEFT JOIN LATERAL (
            SELECT to_service_id FROM appeals.assignment
            WHERE request_id = a.request_id
            ORDER BY new_version DESC LIMIT 1
        ) assignment ON true;

        CREATE INDEX appeal_received_analytics_idx
            ON appeals.appeal(region_id, received_at)
            WHERE received_at_quality IN ('exact', 'source_tz_assumed');

        CREATE TABLE analytics.intent_alias (
            entity_type varchar(16) NOT NULL CHECK (entity_type IN ('region','topic','service')),
            entity_id varchar(128) NOT NULL,
            alias varchar(256) NOT NULL CHECK (length(trim(alias)) > 0),
            version varchar(64) NOT NULL,
            effective_from timestamptz NOT NULL,
            effective_to timestamptz,
            synthetic_only boolean NOT NULL DEFAULT true,
            approval_ref varchar(256),
            PRIMARY KEY (entity_type,entity_id,alias,version),
            CHECK (effective_to IS NULL OR effective_to > effective_from),
            CHECK (synthetic_only OR length(trim(approval_ref)) > 0 AND approval_ref IS NOT NULL)
        );
        CREATE TRIGGER intent_alias_append_only
            BEFORE UPDATE OR DELETE ON analytics.intent_alias
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();

        CREATE TABLE analytics.ask_audit (
            query_id uuid PRIMARY KEY,
            actor_token varchar(256) NOT NULL,
            region_scope varchar(32) NOT NULL,
            question_hash char(64) NOT NULL CHECK (question_hash ~ '^[a-f0-9]{64}$'),
            locale varchar(16) NOT NULL,
            parser_version varchar(128) NOT NULL,
            intent jsonb,
            validated_query jsonb,
            status varchar(32) NOT NULL,
            reason_code varchar(128),
            data_cutoff timestamptz,
            quality varchar(16),
            records_considered bigint NOT NULL DEFAULT 0,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TRIGGER ask_audit_append_only
            BEFORE UPDATE OR DELETE ON analytics.ask_audit
            FOR EACH ROW EXECUTE FUNCTION audit.reject_append_only_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TABLE analytics.ask_audit")
    op.execute("DROP TABLE analytics.intent_alias")
    op.execute("DROP INDEX appeals.appeal_received_analytics_idx")
    op.execute("DROP VIEW analytics.appeal_read_model")
